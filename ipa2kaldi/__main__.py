"""Command-line interface for ipa2kaldi"""
import argparse
import importlib
import logging
import shutil
import typing
from collections import Counter
from pathlib import Path

import gruut
from gruut.utils import WordPronunciation
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

    if args.noise_dir:
        args.noise_dir = Path(args.noise_dir)

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
    gruut_lang = gruut.Language.load(args.language, preload_lexicon=True)
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
        dataset_type = "default"

        if len(dataset_parts) > 1:
            dataset_name = dataset_parts[1]

            # <type>:<name>
            name_parts = dataset_name.split(":", maxsplit=1)
            if len(name_parts) == 2:
                dataset_type, dataset_name = name_parts

        dataset_module = importlib.import_module(
            f".dataset.{dataset_type}", __package__
        )

        _LOGGER.debug("Loading dataset from %s (type=%s)", dataset_path, dataset_type)
        dataset = Dataset(index=dataset_index, name=dataset_name, path=dataset_path)
        datasets[dataset.name] = dataset

        # Load transcriptions
        num_items_loaded = 0
        num_items_dropped = 0

        for item_index, item_details in enumerate(
            dataset_module.get_metadata(dataset_path)
        ):
            item_speaker, item_text, audio_path = (
                item_details[0],
                item_details[1],
                item_details[2],
            )

            if not audio_path.is_file():
                missing_files[dataset.name] += 1
                _LOGGER.warning(
                    "Missing audio file for item %s: %s", item_index, audio_path
                )
                continue

            # start/end
            item_start_ms: typing.Optional[int] = None
            item_end_ms: typing.Optional[int] = None

            if len(item_details) > 3:
                item_start_ms = item_details[3]

            if len(item_details) > 4:
                item_end_ms = item_details[4]

            clean_words = []

            # Tokenize and find missing words
            drop_item = False
            for sentence in gruut_lang.tokenizer.tokenize(item_text):
                if drop_item:
                    break

                for word in sentence.clean_words:
                    if gruut_lang.tokenizer.is_word(word):
                        clean_words.append(word)
                        lexicon_words.add(word)

                        if word not in lexicon:
                            if args.drop_unknown:
                                # Drop instead of guessing pronunications
                                drop_item = True
                                num_items_dropped += 1
                                break

                            missing_words.add(word)

            if drop_item:
                _LOGGER.debug(
                    "Dropped item %s due to unknown words (%s)", item_index, item_text
                )
                continue

            clean_item_text = " ".join(clean_words)

            # Unique index of speaker
            speaker_index = dataset.speaker_indexes.get(item_speaker)
            if speaker_index is None:
                speaker_index = len(dataset.speaker_indexes)
                dataset.speaker_indexes[item_speaker] = speaker_index

            item = DatasetItem(
                index=item_index,
                dataset_index=dataset_index,
                speaker=item_speaker,
                speaker_index=speaker_index,
                text=clean_item_text,
                path=audio_path,
                start_ms=item_start_ms,
                end_ms=item_end_ms,
            )

            dataset.items.append(item)
            num_items_loaded += 1

        # ---------------------------------------------------------------------

        _LOGGER.info(
            "Loaded %s item(s) from dataset %s (dropped %s)",
            num_items_loaded,
            dataset_name,
            num_items_dropped,
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

        # Write missing words to text file
        missing_words_path = args.recipe_dir / "missing_words.txt"
        with open(missing_words_path, "w") as missing_words_file:
            for word in sorted(missing_words):
                print(word, file=missing_words_file)

        # Guess pronunciations
        missing_words_dict_path = args.recipe_dir / "missing_words.dict"
        with open(missing_words_dict_path, "w") as missing_words_dict_file:
            for word, word_pron in gruut_lang.phonemizer.predict(
                missing_words, nbest=1
            ):
                # Assume one guess
                word_pron = WordPronunciation(
                    phonemes=[
                        p.text
                        for p in gruut_lang.phonemes.split(
                            "".join(word_pron), keep_stress=gruut_lang.keep_stress
                        )
                    ]
                )
                lexicon[word] = [word_pron]
                lexicon_words.add(word)
                print(word, " ".join(word_pron.phonemes), file=missing_words_dict_file)

        _LOGGER.debug(
            "Wrote missing words to %s and %s. Add with --lexicon",
            missing_words_path,
            missing_words_dict_path,
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
                print(word, *word_pron.phonemes, file=lexicon_file)

    # -------------------------------------------------------------------------
    # Write Kaldi recipe files
    # -------------------------------------------------------------------------

    _LOGGER.debug("Writing Kaldi recipe files")

    # Datasets
    write_test_train(
        args.recipe_dir,
        datasets.values(),
        noise_dir=args.noise_dir,
        noise_stride=args.noise_stride,
    )

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
    parser.add_argument("--language", required=True, help="Language code (e.g., en-us)")
    parser.add_argument(
        "--recipe-dir",
        required=True,
        help="Path to Kaldi recipe dir (e.g., egs/rhasspy_en-us)",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        action="append",
        nargs="+",
        metavar=("path", "type:name"),
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
        "--drop-unknown",
        action="store_true",
        help="Drop utterances with unknown instead of guessing pronunciations",
    )
    parser.add_argument(
        "--noise-dir",
        help="Path to directory with noise WAV files (_background_, SIL, NSN, etc.)",
    )
    parser.add_argument(
        "--noise-stride",
        type=int,
        default=4,
        help="Add noise to every nth clip (default: 4, only with --noise-dir)",
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
