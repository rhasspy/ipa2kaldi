"""Utility methods for ipa2kaldi"""
import gzip
import subprocess
import typing
from pathlib import Path

_SILENCE_WORDS = {"<s>", "</s>"}

# -----------------------------------------------------------------------------


def maybe_gzip_open(
    path_or_str: typing.Union[Path, str], mode: str = "r", create_dir: bool = True
) -> typing.IO[typing.Any]:
    """Opens a file as gzip if it has a .gz extension."""
    if create_dir and mode in {"w", "a"}:
        Path(path_or_str).parent.mkdir(parents=True, exist_ok=True)

    if str(path_or_str).endswith(".gz"):
        if mode == "r":
            gzip_mode = "rt"
        elif mode == "w":
            gzip_mode = "wt"
        elif mode == "a":
            gzip_mode = "at"
        else:
            gzip_mode = mode

        return gzip.open(path_or_str, gzip_mode)

    return open(path_or_str, mode)


def ensure_symlink_dir(target_path: Path, link_path: Path):
    """Ensures that a directory symlink exists and is not broken."""
    if not link_path.is_dir():
        if link_path.is_symlink():
            # Remove bad symlink
            link_path.unlink()

        link_path.symlink_to(target_path, target_is_directory=True)


def read_arpa(
    arpa_file, silence_words=None
) -> typing.Iterable[typing.Tuple[str, float]]:
    """Load single words and log-likelihoods from ARPA language model"""
    if silence_words is None:
        silence_words = _SILENCE_WORDS

    in_1grams = False
    for line in arpa_file:
        line = line.strip()
        if not line:
            continue

        if line.startswith("\\"):
            if in_1grams:
                # Must be past 1-grams now
                break

            if line == "\\1-grams:":
                in_1grams = True
        elif in_1grams:
            # Parse 1-gram
            prob, word, *_ = line.split()
            prob = float(prob)
            word = word.strip()

            if (not word) or (word in silence_words):
                # Skip empty or ignored words
                continue

            yield word, prob


# -----------------------------------------------------------------------------


def get_duration(audio_path: typing.Union[str, Path], stream_num: int = 0) -> float:
    """Get the duration of an audio file in seconds (requires ffmpeg/ffprobe)"""
    duration_str = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            f"a:{stream_num}",
            "-show_entries",
            "stream=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        universal_newlines=True,
    )

    return float(duration_str)
