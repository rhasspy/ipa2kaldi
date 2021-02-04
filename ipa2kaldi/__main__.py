"""Command-line interface for ipa2kaldi"""
import argparse
import logging
import re
import shutil
import typing
from collections import Counter
from pathlib import Path

import phonetisaurus

import gruut
from ipa2kaldi import (
    Dataset,
    DatasetItem,
    copy_recipe_files,
    write_phones,
    write_test_train,
)
from ipa2kaldi.utils import ensure_symlink_dir, maybe_gzip_open, read_arpa

_LOGGER = logging.getLogger("ipa2kaldi")

_DIR = Path(__file__).parent

# -----------------------------------------------------------------------------


def main():
    """Main entry point"""
    args = get_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    _LOGGER.debug(args)

    # Convert to paths
    args.recipe_dir = Path(args.recipe_dir)
    args.lexicon = [Path(l) for l in args.lexicon]

    if args.arpa_lm:
        args.arpa_lm = Path(args.arpa_lm)

    # Create recipe directory
    args.recipe_dir.mkdir(parents=True, exist_ok=True)

    kaldi_dir = args.recipe_dir.parent.parent.parent
    _LOGGER.info("Assuming Kaldi is located at %s", kaldi_dir)

    egs_dir = kaldi_dir / "egs"
    assert egs_dir.is_dir(), "Recipe directory must be at kaldi/egs/<name>/<version>"

    steps_dir = egs_dir / "wsj" / "s5" / "steps"
    utils_dir = egs_dir / "wsj" / "s5" / "utils"

    # Create WSJ symlinks:
    # steps -> egs/wsj/s5/steps
    # utils -> egs/wsj/s5/utils
    ensure_symlink_dir(steps_dir, args.recipe_dir / "steps")
    ensure_symlink_dir(utils_dir, args.recipe_dir / "utils")

    # Load language
    gruut_lang = gruut.Language.load(args.language)
    assert gruut_lang, f"Unsupported language: {args.language}"
    lexicon = gruut_lang.phonemizer.lexicon

    # Load additional lexicons
    for lexicon_path in args.lexicon:
        _LOGGER.debug("Loading lexicon from %s", lexicon_path)

        with open(lexicon_path, "r") as lexicon_file:
            gruut.utils.load_lexicon(
                lexicon_file, lexicon=lexicon, casing=gruut_lang.tokenizer.casing
            )

    # -------------------------------------------------------------------------
    # Load datasets
    # -------------------------------------------------------------------------

    datasets: typing.Dict[str, Dataset] = {}
    lexicon_words: typing.Set[str] = set()
    missing_words: typing.Set[str] = set()
    missing_files = Counter()

    for dataset_index, dataset_parts in enumerate(args.dataset):
        dataset_path = Path(dataset_parts[0])
        dataset_name = dataset_path.name
        dataset_speaker = None

        if len(dataset_parts) > 1:
            dataset_name = dataset_parts[1]

        if len(dataset_parts) > 2:
            dataset_speaker = dataset_parts[2]

        _LOGGER.debug("Loading dataset from %s", dataset_path)
        dataset = Dataset(
            index=dataset_index,
            name=dataset_name,
            path=dataset_path,
            speaker=dataset_speaker,
        )
        datasets[dataset.name] = dataset

        # Load transcriptions
        metadata_path = dataset.path / "metadata.csv"
        num_items_loaded = 0

        with open(metadata_path, "r") as metadata_file:
            for line_index, line in enumerate(metadata_file):
                line = line.strip()
                if not line:
                    continue

                try:
                    if dataset.speaker:
                        # Speaker was provided
                        item_id, item_text = line.split("|", maxsplit=1)
                        item_speaker = dataset.speaker
                    else:
                        # Speaker is in metadata
                        item_id, item_speaker, item_text = line.split("|", maxsplit=2)
                except ValueError as e:
                    _LOGGER.exception(
                        "Error on line %s of %s: %s",
                        line_index + 1,
                        metadata_path,
                        line,
                    )
                    raise e

                item_id = item_id.strip()
                item_speaker = item_speaker.strip()
                item_text = item_text.strip()

                if not item_id:
                    missing_files[dataset.name] += 1
                    _LOGGER.warning("Missing id for %s", line)
                    continue

                if not item_speaker:
                    missing_files[dataset.name] += 1
                    _LOGGER.warning("Missing speaker for %s", line)
                    continue

                if not item_text:
                    missing_files[dataset.name] += 1
                    _LOGGER.warning("Missing text for %s", line)
                    continue

                audio_path = dataset.path / (item_id + ".wav")
                if not audio_path.is_file():
                    missing_files[dataset.name] += 1
                    _LOGGER.warning(
                        "Missing audio file for id %s: %s", item_id, audio_path
                    )
                    continue

                clean_words = []

                # Tokenize and find missing words
                for sentence in gruut_lang.tokenizer.tokenize(item_text):
                    for word in sentence.clean_words:
                        if gruut_lang.tokenizer.is_word(word):
                            clean_words.append(word)
                            lexicon_words.add(word)

                            if word not in lexicon:
                                missing_words.add(word)

                clean_item_text = " ".join(clean_words)

                # Unique index of speaker
                speaker_index = dataset.speaker_indexes.get(item_speaker)
                if speaker_index is None:
                    speaker_index = len(dataset.speaker_indexes)
                    dataset.speaker_indexes[item_speaker] = speaker_index

                item = DatasetItem(
                    index=line_index,
                    id=item_id,
                    dataset_index=dataset_index,
                    speaker=item_speaker,
                    speaker_index=speaker_index,
                    text=clean_item_text,
                    path=audio_path,
                )

                dataset.items[item.id] = item
                num_items_loaded += 1

        # ---------------------------------------------------------------------

        _LOGGER.debug(
            "Loaded %s item(s) from dataset %s", num_items_loaded, dataset_name
        )

    # -------------------------------------------------------------------------

    for dataset_name, num_missing in missing_files.most_common():
        total_items = num_missing + len(datasets[dataset_name].items)
        _LOGGER.warning(
            "Missing files from %s: %s/%s", dataset_name, num_missing, total_items
        )

    # -------------------------------------------------------------------------
    # Guess missing words
    # -------------------------------------------------------------------------

    if missing_words:
        _LOGGER.debug(
            "Guessing pronunciations for %s missing word(s)", len(missing_words)
        )

        missing_words_path = args.recipe_dir / "missing_words.txt"

        with open(missing_words_path, "w") as missing_words_file:
            for word, word_pron in gruut_lang.phonemizer.predict(
                missing_words, nbest=1
            ):
                # Assume one guess
                word_pron = [
                    p.text
                    for p in gruut_lang.phonemes.split(
                        "".join(word_pron), keep_stress=gruut_lang.keep_stress
                    )
                ]
                lexicon[word] = [word_pron]
                lexicon_words.add(word)
                print(word, " ".join(word_pron), file=missing_words_file)

        _LOGGER.debug(
            "Wrote missing words to %s. Add with --lexicon", missing_words_path
        )

    # -------------------------------------------------------------------------
    # Write final lexicon
    # -------------------------------------------------------------------------

    recipe_lexicon_path = args.recipe_dir / "data" / "local" / "dict" / "lexicon.txt.gz"
    _LOGGER.debug("Writing final lexicon to %s", recipe_lexicon_path)

    with maybe_gzip_open(recipe_lexicon_path, "w") as lexicon_file:
        if args.unknown_word:
            # Add unknown word
            lexicon_words.add(args.unknown_word)
            print(args.unknown_word, args.unknown_phone, file=lexicon_file)

        if args.silence_word:
            # Add silence word
            print(args.silence_word, args.silence_phone, file=lexicon_file)

        for word, word_prons in lexicon.items():
            for word_pron in word_prons:
                print(word, *word_pron, file=lexicon_file)

    # -------------------------------------------------------------------------
    # Write Kaldi recipe files
    # -------------------------------------------------------------------------

    _LOGGER.debug("Writing Kaldi recipe files")

    # Datasets
    write_test_train(args.recipe_dir, datasets.values())

    # Phones
    nonsilence_phones = []
    for phoneme in gruut_lang.phonemes:
        # No tones
        nonsilence_phones.append(phoneme.text)

        if phoneme.tones:
            # Separate phoneme for each tone
            for tone in phoneme.tones:
                nonsilence_phones.append(phoneme.text + tone)

    write_phones(args.recipe_dir, nonsilence_phones, add_stress=gruut_lang.keep_stress)

    # Scripts
    copy_recipe_files(args.recipe_dir, _DIR / "recipe")

    # Check for ARPA LM
    lm_path = args.recipe_dir / "lm" / "lm.arpa.gz"

    if args.arpa_lm:
        _LOGGER.debug("Copying ARPA language model (%s -> %s)", args.arpa_lm, lm_path)
        with maybe_gzip_open(lm_path, "w") as dest_lm_file:
            with maybe_gzip_open(args.arpa_lm, "r") as src_lm_file:
                shutil.copyfileobj(src_lm_file, dest_lm_file)

    if lm_path.is_file():
        _LOGGER.debug("Checking if all words in the lexicon are in %s", lm_path)
        with maybe_gzip_open(lm_path, "r") as lm_file:
            arpa_words = set(w for w, _ in read_arpa(lm_file))

        missing_arpa_words = lexicon_words - arpa_words
        if missing_arpa_words:
            _LOGGER.warning(
                "Missing %s word(s) from ARPA LM: %s",
                len(missing_arpa_words),
                missing_arpa_words,
            )
    else:
        _LOGGER.warning("Make sure to put ARPA language model at %s", lm_path)

    _LOGGER.info("Done")


# -----------------------------------------------------------------------------


def get_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(prog="ipa2kaldi")
    parser.add_argument("language", help="Language code (e.g., en-us)")
    parser.add_argument(
        "recipe_dir", help="Path to Kaldi recipe dir (e.g., egs/rhasspy_en-us)"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        action="append",
        nargs="+",
        help="Path to dataset directory with audio files and metadata.csv",
    )
    parser.add_argument(
        "--lexicon",
        action="append",
        default=[],
        help="Path to additional lexicon to load",
    )
    parser.add_argument(
        "--unknown-word",
        default="<unk>",
        help="Lexicon entry for unknown word (default: <unk>)",
    )
    parser.add_argument(
        "--unknown-phone",
        default="SPN",
        help="Silence phone for unknown word (default: SPN)",
    )
    parser.add_argument(
        "--silence-word",
        default="!SIL",
        help="Lexicon entry for silence (default: !SIL)",
    )
    parser.add_argument(
        "--silence-phone", default="SIL", help="Silence phone (default: SIL)"
    )
    parser.add_argument(
        "--arpa-lm",
        help="Path to ARPA language model (copied to <RECIPE>/lm/lm.arpa.gz)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to console"
    )

    # # Create subparsers for each sub-command
    # sub_parsers = parser.add_subparsers()
    # sub_parsers.required = True
    # sub_parsers.dest = "command"

    # # ---------
    # # text2arpa
    # # ---------
    # text2arpa_parser = sub_parsers.add_parser(
    #     "text2arpa", help="Generate WAV data for IPA phonemes"
    # )
    # text2arpa_parser.set_defaults(func=do_text2arpa)

    # # Shared arguments
    # for sub_parser in [text2arpa_parser, recipe_parser]:
    #     sub_parser.add_argument(
    #         "--debug", action="store_true", help="Print DEBUG messages to console"
    #     )

    return parser.parse_args()


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
