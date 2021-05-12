#!/usr/bin/env python3
"""
Converts a Lingua-Libre dataset
"""
import argparse
import csv
import json
import sys
import typing
from pathlib import Path
from uuid import uuid4


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from dataset"""
    for speaker_dir in dataset_dir.iterdir():
        if not speaker_dir.is_dir():
            continue

        speaker_id = speaker_dir.name
        for ogg_path in speaker_dir.glob("*.ogg"):
            text = ogg_path.stem
            yield speaker_id, text, ogg_path


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="linga_lig.py")
    parser.add_argument(
        "dataset_dir", help="Path to directory with speaker directories"
    )
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, wav_path in get_metadata(args.dataset_dir):
        writer.writerow((str(wav_path), speaker_id, text))
