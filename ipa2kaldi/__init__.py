"""Methods and classes for ipa2kaldi"""
import functools
import logging
import random
import shutil
import typing
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from gruut_ipa import IPA

from .utils import get_duration

_LOGGER = logging.getLogger("ipa2kaldi")

_DIR = Path(__file__).parent
_ADD_NOISE = (_DIR.parent / "bin" / "add_noise.sh").absolute()

# Default silence phones.
# SIL = actual silence
# SPN = spoken noise (unknown words)
# NSN = non-spoken noise (background noise)
_SILENCE_PHONES = ["SIL", "SPN", "NSN"]

# -----------------------------------------------------------------------------


@dataclass
class DatasetItem:
    """Single item from a dataset"""

    index: int
    dataset_index: int
    speaker: str
    speaker_index: int
    text: str
    path: Path
    start_ms: typing.Optional[int] = None
    end_ms: typing.Optional[int] = None

    @property
    def dataset_speaker(self) -> str:
        """Get globally-unique id for speaker"""
        return f"d{self.dataset_index}-s{self.speaker_index}"


@dataclass
class Dataset:
    """Entire dataset"""

    index: int
    name: str
    path: Path
    speaker: typing.Optional[str] = None
    items: typing.List[DatasetItem] = field(default_factory=list)
    speaker_indexes: typing.Dict[str, int] = field(default_factory=dict)


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


def write_test_train(
    recipe_dir: Path,
    datasets: typing.Iterable[Dataset],
    test_percentage: float = 5,
    use_ffmpeg: bool = True,
    noise_dir: typing.Optional[typing.Union[str, Path]] = None,
    noise_background_name: str = "_background_",
    noise_foreground_skip_prefix: str = "_",
    noise_stride: int = 4,
):
    """Write wav.scp, text, and utt2spk files for test/train data splits."""

    # path -> duration_sec
    noise_backgrounds: typing.Dict[Path, float] = {}
    noise_bg_paths: typing.List[Path] = []

    # path -> (label, duration_sec)
    noise_foregrounds: typing.Dict[Path, typing.Tuple[str, float]] = {}
    noise_fg_paths: typing.List[Path] = []

    if noise_dir is not None:
        # Load details from noise data
        noise_dir = Path(noise_dir)

        # Load background
        noise_bg_dir = noise_dir / noise_background_name
        _LOGGER.debug("Loading noise background durations from %s", noise_bg_dir)

        bg_durations_path = noise_bg_dir / "durations.txt"
        if bg_durations_path.is_file():
            # Load durations from cache
            with open(bg_durations_path, "r") as bg_durations_file:
                for line in bg_durations_file:
                    line = line.strip()
                    if not line:
                        continue

                    wav_name, duration_str = line.split("|")
                    bg_wav_path = noise_bg_dir / wav_name

                    noise_backgrounds[bg_wav_path] = float(duration_str)
                    noise_bg_paths.append(bg_wav_path)
        else:
            noise_bg_paths = list(noise_bg_dir.rglob("*.wav"))

            # Get durations in parallel
            with ThreadPoolExecutor() as executor:
                bg_wav_durations = executor.map(get_duration, noise_bg_paths)

            noise_backgrounds.update(zip(noise_bg_paths, bg_wav_durations))

        total_bg_seconds = sum(noise_backgrounds.values())

        _LOGGER.debug(
            "Found %s second(s) in %s background WAV file(s)",
            total_bg_seconds,
            len(noise_backgrounds),
        )

        # Load foreground
        for noise_fg_dir in noise_dir.iterdir():
            if (not noise_fg_dir.is_dir()) or (
                noise_fg_dir.name.startswith(noise_foreground_skip_prefix)
            ):
                continue

            _LOGGER.debug("Loading noise foreground durations from %s", noise_fg_dir)

            # Directory name is a Kaldi word like SIL, NSN, SPN, etc.
            fg_label = noise_fg_dir.name

            fg_durations_path = noise_fg_dir / "durations.txt"
            if fg_durations_path.is_file():
                # Load durations from cache
                with open(fg_durations_path, "r") as fg_durations_file:
                    for line in fg_durations_file:
                        line = line.strip()
                        if not line:
                            continue

                        wav_name, duration_str = line.split("|")
                        fg_wav_path = noise_fg_dir / wav_name

                        noise_foregrounds[fg_wav_path] = (fg_label, float(duration_str))
                        noise_fg_paths.append(fg_wav_path)
            else:
                # Get durations in parallel
                fg_wav_paths = list(noise_fg_dir.rglob("*.wav"))
                noise_fg_paths.extend(fg_wav_paths)

                with ThreadPoolExecutor() as executor:
                    fg_wav_durations = executor.map(get_duration, fg_wav_paths)

                noise_foregrounds.update(
                    zip(
                        fg_wav_paths,
                        ((fg_label, fg_duration) for fg_duration in fg_wav_durations),
                    )
                )

        total_fg_seconds = sum(fg_sec for _, fg_sec in noise_foregrounds.values())
        _LOGGER.debug(
            "Found %s second(s) in %s foreground WAV file(s)",
            total_fg_seconds,
            len(noise_foregrounds),
        )

    # -------------------------------------------------------------------------

    utterances: typing.Dict[str, DatasetItem] = {}
    for dataset in datasets:
        for item in dataset.items:
            utterance_id = f"{item.dataset_speaker}-i{item.index}"
            utterances[utterance_id] = item

    # 5% test
    num_test_ids = int(len(utterances) / (100 / test_percentage))

    # 90% train
    # num_train_ids = len(utterances) - num_test_ids

    # Split data into test/train sets
    test_ids = set(random.sample(utterances.keys(), num_test_ids))
    train_ids = utterances.keys() - test_ids

    _LOGGER.debug(
        "Training item(s): %s, testing item(s): %s", len(train_ids), len(test_ids)
    )

    # Write wav.scp, text, utt2spk files for each set
    for dir_name, utt_ids in [("test", test_ids), ("train", train_ids)]:
        data_dir = recipe_dir / "data" / dir_name
        data_dir.mkdir(parents=True, exist_ok=True)

        # Files need to be in sorted order
        utt_speaker = sorted(
            [(utt_id, utterances[utt_id].dataset_speaker) for utt_id in utt_ids]
        )

        # Dataset items to generate noisy variants of
        noisy_items: typing.Dict[str, DatasetItem] = {}

        # wav.scp, text, utt2spk
        with open(data_dir / "wav.scp", "w") as wav_scp, open(
            data_dir / "text", "w"
        ) as text_file, open(data_dir / "utt2spk", "w") as utt2spk:
            for utt_index, (utt_id, speaker) in enumerate(utt_speaker):
                utt: DatasetItem = utterances[utt_id]

                if (noise_dir is not None) and ((utt_index % noise_stride) == 0):
                    # Emit noisy version of audio clip
                    noisy_items[utt_id] = utt

                # wav.scp
                file_path = utt.path.absolute()
                if use_ffmpeg:
                    seek_trim = []
                    if utt.start_ms is not None:
                        start_sec = utt.start_ms / 1000
                        seek_trim.extend(["-ss", str(start_sec)])

                    if utt.end_ms is not None:
                        start_ms = 0 if (utt.start_ms is None) else utt.start_ms
                        duration_ms = utt.end_ms - start_ms
                        if duration_ms > 0:
                            duration_sec = duration_ms / 1000
                            seek_trim.extend(["-t", str(duration_sec)])
                        else:
                            _LOGGER.warning("Negative duration for %s", utt)

                            # Drop utterance
                            continue

                    # Convert file to a 16-bit 16khz mono WAV
                    print(
                        utt_id,
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(file_path),
                        *seek_trim,
                        "-ar",
                        "16000",
                        "-ac",
                        "1",
                        "-acodec",
                        "pcm_s16le",
                        "-f",
                        "wav",
                        "-",
                        "|",
                        file=wav_scp,
                    )
                else:
                    # File must already be a 16-bit 16khz mono WAV
                    print(utt_id, str(file_path), file=wav_scp)

                # text
                print(utt_id, utt.text.strip(), file=text_file)

                # utt2spk
                print(utt_id, speaker, file=utt2spk)

            # Generate noisy items in parallel
            if noisy_items:
                with ThreadPoolExecutor() as executor:
                    _LOGGER.debug(
                        "Generating %s noisy item(s) for %s", len(noisy_items), dir_name
                    )

                    for wav_scp_line, text_line, utt2spk_line in executor.map(
                        functools.partial(
                            generate_noisy,
                            speaker,
                            noise_backgrounds,
                            noise_bg_paths,
                            noise_foregrounds,
                            noise_fg_paths,
                        ),
                        noisy_items.items(),
                    ):
                        # Write noisy versions to files
                        print(wav_scp_line, file=wav_scp)
                        print(text_line, file=text_file)
                        print(utt2spk_line, file=utt2spk)


# -----------------------------------------------------------------------------


def generate_noisy(
    speaker: str,
    noise_backgrounds: typing.Dict[Path, float],
    noise_bg_paths: typing.List[Path],
    noise_foregrounds: typing.Dict[Path, typing.Tuple[str, float]],
    noise_fg_paths: typing.List[Path],
    id_utt: typing.Tuple[str, DatasetItem],
) -> typing.Tuple[str, str, str]:
    """Emits noisy wav.scp, text, and utt2spk lines for dataset item"""
    utt_id, utt = id_utt

    # Credit: https://github.com/gooofy/zamia-speech/blob/master/speech_gen_noisy.py
    noisy_utt_id = f"n-{utt_id}"
    file_path = utt.path.absolute()

    start_sec: typing.Optional[float] = None
    duration_sec: typing.Optional[float] = None

    if utt.start_ms is not None:
        start_sec = utt.start_ms / 1000

    if utt.end_ms is not None:
        start_ms = 0 if (utt.start_ms is None) else utt.start_ms
        duration_ms = utt.end_ms - start_ms
        if duration_ms > 0:
            duration_sec = duration_ms / 1000

    fg_duration = duration_sec

    if fg_duration is None:
        # Read audio file and get duration
        fg_duration = get_duration(file_path)

    assert fg_duration is not None

    # Get a random background WAV.
    # This will be mixed in behind the entire noisy clip.
    bg_path = random.choice(noise_bg_paths)
    bg_duration = noise_backgrounds[bg_path]

    # Get 2 random foreground WAVs.
    # These will be placed at the start and end of the clip.
    fg_path_1 = random.choice(noise_fg_paths)
    fg_label_1, fg_duration_1 = noise_foregrounds[fg_path_1]

    fg_path_2 = random.choice(noise_fg_paths)
    fg_label_2, fg_duration_2 = noise_foregrounds[fg_path_2]

    # Duration of entire noisy clip
    total_noise_sec = fg_duration_1 + fg_duration + fg_duration_2

    # Offset into background WAV.
    # Used to trim.
    bg_offset = random.uniform(0, max(0, bg_duration - total_noise_sec))

    # Normalization levels of background/foreground
    bg_level = random.uniform(-15, -10)
    fg_level = random.uniform(-1, 0)

    # Amount of reverb to add
    reverb = random.uniform(0, 50)

    wav_scp = " ".join(
        [
            noisy_utt_id,
            str(_ADD_NOISE),
            str(file_path),
            str(fg_path_1),
            str(fg_path_2),
            str(bg_path),
            str(bg_offset),
            str(total_noise_sec),
            str(start_sec) if (start_sec is not None) else "''",
            str(duration_sec) if (duration_sec is not None) else "''",
            str(fg_level),
            str(bg_level),
            str(reverb),
            "|",
        ]
    )

    # text with foreground labels on either side (e.g., NSN ...(text)... SIL)
    noisy_text = " ".join([noisy_utt_id, fg_label_1, utt.text.strip(), fg_label_2])

    # Same speaker
    utt2spk = " ".join([noisy_utt_id, speaker])

    return wav_scp, noisy_text, utt2spk


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
