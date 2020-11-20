"""Methods and classes for ipa2kaldi"""
import logging
import random
import shutil
import typing
from dataclasses import dataclass, field
from pathlib import Path

from gruut_ipa import IPA

_LOGGER = logging.getLogger("ipa2kaldi")

# Default silence phones.
# SIL = actual silence
# SPN = spoken noise (unknown words)
# NSN = non-spoken noise (background noise)
_SILENCE_PHONES = ["SIL", "SPN", "NSN"]

# -----------------------------------------------------------------------------


@dataclass
class DatasetItem:
    """Single item from a dataset"""

    id: str
    speaker: str
    text: str
    path: Path


@dataclass
class Dataset:
    """Entire dataset"""

    name: str
    path: Path
    speaker: typing.Optional[str] = None
    items: typing.Dict[str, DatasetItem] = field(default_factory=dict)


# -----------------------------------------------------------------------------


def copy_recipe_files(recipe_dir: Path, source_dir: Path):
    """Copy files to Kaldi recipe."""
    for source_path in source_dir.rglob("*"):
        if not source_path.is_file():
            continue

        rel_path_str = str(source_path.relative_to(source_dir))
        dest_path = recipe_dir / rel_path_str

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.is_file():
            dest_path.unlink()

        shutil.copy2(source_path, dest_path)


# -----------------------------------------------------------------------------


def write_test_train(recipe_dir: Path, datasets: typing.Iterable[Dataset]):
    """Write wav.scp, text, and utt2spk files for test/train data splits."""
    utterances: typing.Dict[str, DatasetItem] = {}
    for dataset in datasets:
        for item in dataset.items.values():
            utterance_id = f"{item.speaker}-{dataset.name}-{item.id}"

            # Remove spaces
            utterance_id = utterance_id.replace(" ", "_")

            utterances[utterance_id] = item

    # 10% test
    num_test_ids = int(len(utterances) / 10)

    # 90% train
    num_train_ids = len(utterances) - num_test_ids

    # Split data into test/train sets
    test_ids = set(random.sample(utterances.keys(), num_test_ids))
    train_ids = utterances.keys() - test_ids

    # Write wav.scp, text, utt2spk files for each set
    for dir_name, utt_ids in [("test", test_ids), ("train", train_ids)]:
        data_dir = recipe_dir / "data" / dir_name
        data_dir.mkdir(parents=True, exist_ok=True)

        # Files need to be in sorted order
        utt_speaker = sorted(
            [(utt_id, utterances[utt_id].speaker) for utt_id in utt_ids]
        )

        # wav.scp
        with open(data_dir / "wav.scp", "w") as wav_scp:
            # text
            with open(data_dir / "text", "w") as text_file:
                # utt2spk
                with open(data_dir / "utt2spk", "w") as utt2spk:
                    for utt_id, speaker in utt_speaker:
                        utt = utterances[utt_id]

                        # wav.scp
                        file_path = utt.path.absolute()
                        print(utt_id, str(file_path), file=wav_scp)

                        # text
                        print(utt_id, utt.text.strip(), file=text_file)

                        # utt2spk
                        print(utt_id, speaker, file=utt2spk)


# -----------------------------------------------------------------------------


def write_phones(
    recipe_dir: Path,
    nonsilence_phones: typing.List[str],
    silence_phones: typing.Optional[typing.List[str]] = None,
    optional_silence_phones: typing.Optional[typing.List[str]] = None,
    add_stress: bool = False,
):
    """Write phone text files for Kaldi recipe."""
    silence_phones = silence_phones or _SILENCE_PHONES
    optional_silence_phones = optional_silence_phones or [silence_phones[0]]

    # Write phone files
    dict_dir: Path = recipe_dir / "data" / "local" / "dict"
    dict_dir.mkdir(parents=True, exist_ok=True)

    nonsilence_path: Path = dict_dir / "nonsilence_phones.txt"
    silence_path: Path = dict_dir / "silence_phones.txt"
    optional_silence_path: Path = dict_dir / "optional_silence.txt"
    extra_questions_path: Path = dict_dir / "extra_questions.txt"

    # nonsilence_phones.txt
    with open(nonsilence_path, "w") as nonsilence_file:
        for phone in nonsilence_phones:
            if add_stress:
                # p ˈp ˌp
                print(
                    phone,
                    f"{IPA.STRESS_PRIMARY.value}{phone}",
                    f"{IPA.STRESS_SECONDARY.value}{phone}",
                    file=nonsilence_file,
                )
            else:
                print(phone, file=nonsilence_file)

    # silence_phones.txt
    with open(silence_path, "w") as silence_file:
        for phone in sorted(silence_phones):
            print(phone, file=silence_file)

    # optional_silence.txt
    with open(optional_silence_path, "w") as optional_silence_file:
        for phone in sorted(optional_silence_phones):
            print(phone, file=optional_silence_file)

    # extra_questions.txt
    with open(extra_questions_path, "w") as extra_questions_file:
        # Silence phones first
        print(*silence_phones, file=extra_questions_file)

        # Non-silence phones next
        print(*nonsilence_phones, file=extra_questions_file)

        if add_stress:
            # Primary stressed phones
            print(
                *[f"{IPA.STRESS_PRIMARY.value}{p}" for p in nonsilence_phones],
                file=extra_questions_file,
            )

            # Secondary stressed phones
            print(
                *[f"{IPA.STRESS_SECONDARY.value}{p}" for p in nonsilence_phones],
                file=extra_questions_file,
            )
