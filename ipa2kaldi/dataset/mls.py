#!/usr/bin/env python3
"""
Converts MLS datasets
"""
import argparse
import csv
import json
import sys
import typing
from pathlib import Path


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from mls dataset"""
    # <parition>/audio/<speaker>/<book>
    for partition in ["dev", "test", "train"]:
        partition_dir = dataset_dir / partition
        audio_dir = partition_dir / "audio"
        transcripts_path = partition_dir / "transcripts.txt"

        with open(transcripts_path, "r") as transcripts_file:
            reader = csv.reader(transcripts_file, delimiter="\t")
            for row in reader:
                utt_id, text = row[0].strip(), row[1].strip()
                speaker_id, book_id, item_id = utt_id.split("_", maxsplit=2)
                flac_path = audio_dir / speaker_id / book_id / f"{utt_id}.flac"

                yield (speaker_id, text, flac_path)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="mls.py")
    parser.add_argument(
        "dataset_dir", help="Path to directory with dev/test/train directories"
    )
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, wav_path in get_metadata(args.dataset_dir):
        writer.writerow((str(wav_path), speaker_id, text))
