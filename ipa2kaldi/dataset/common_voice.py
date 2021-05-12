#!/usr/bin/env python3
"""
Converts Mozilla Common Voice datasets
"""
import argparse
import csv
import sys
import typing
from pathlib import Path


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from Common Voice dataset"""
    validated_path = dataset_dir / "validated.tsv"
    clips_dir = dataset_dir / "clips"

    with open(validated_path, "r") as validate_file:
        reader = csv.reader(validate_file, delimiter="\t")
        # Skip header
        next(reader)

        for row in reader:
            speaker_id = row[0].strip()
            mp3_path = clips_dir / row[1].strip()
            text = row[2].strip()

            yield speaker_id, text, mp3_path


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="m_ailabs.py")
    parser.add_argument("dataset_dir", help="Path to directory with clips directory")
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, audio_path in get_metadata(args.dataset_dir):
        writer.writerow((str(audio_path), speaker_id, text))
