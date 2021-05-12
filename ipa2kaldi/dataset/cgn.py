#!/usr/bin/env python3
"""
Converts CGN dataset
"""
import argparse
import csv
import sys
import typing
from pathlib import Path

# Exclude face-to-face components
_COMPONENTS = [
    # "comp-a",
    "comp-b",
    # "comp-c",
    # "comp-d",
    "comp-e",
    # "comp-f",
    # "comp-g",
    "comp-h",
    "comp-i",
    "comp-j",
    "comp-k",
    "comp-l",
    "comp-m",
    "comp-n",
    "comp-o",
]

_LANGUAGES = ["nl", "vl"]

# -----------------------------------------------------------------------------


def get_metadata(
    dataset_dir: Path
) -> typing.Iterable[typing.Tuple[str, str, Path, int, int]]:
    """Load speaker, text, audio path, start ms, end ms from CGN dataset"""
    wav_base_dir = dataset_dir / "data" / "audio" / "wav"
    sea_base_dir = dataset_dir / "data" / "annot" / "corex" / "sea"

    for component in _COMPONENTS:
        for language in _LANGUAGES:
            wav_dir = wav_base_dir / component / language
            sea_dir = sea_base_dir / component / language

            for sea_path in sea_dir.glob("*.sea"):
                for speaker_id, text, wav_name, start_ms, end_ms in _load_sea(sea_path):
                    wav_path = wav_dir / f"{wav_name}.wav"
                    yield (speaker_id, text, wav_path, start_ms, end_ms)


def _load_sea(sea_path: Path) -> typing.Iterable[typing.Tuple[str, str, str, int, int]]:
    """Load speaker id, text, wav name, start/end ms from sea file"""
    wav_name = ""
    text = ""
    speaker_id = ""
    start_ms = -1
    end_ms = -1

    with open(sea_path, "r", encoding="cp1252") as sea_file:
        for line in sea_file:
            line = line.strip()

            if not line:
                # Next utterance
                wav_name = ""
                text = ""
                speaker_id = ""
                start_ms = -1
                end_ms = -1
                continue

            line_parts = line.split()

            if wav_name:
                line_type = line_parts[0].upper()
                if line_type == "ORT":
                    # Orthographic transcription
                    text = " ".join(line_parts[1:])

                    yield (speaker_id, text, wav_name, start_ms, end_ms)
            else:
                # Header line
                start_ms = int(line_parts[1])
                end_ms = int(line_parts[2])
                speaker_id = line_parts[3]
                wav_name = line_parts[4].split(".", maxsplit=2)[0]


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="cgn.py")
    parser.add_argument("dataset_dir", help="Path to directory with data directory")
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, audio_path, start_ms, end_ms in get_metadata(
        args.dataset_dir
    ):
        writer.writerow((str(audio_path), speaker_id, text, start_ms, end_ms))
