#!/usr/bin/env python3
"""
Converts Arabic Speech Corpus
http://en.arabicspeechcorpus.com/
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
    metadata_path = dataset_dir / "metadata.csv"
    with open(metadata_path, "r") as metadata_file:
        reader = csv.reader(metadata_file, delimiter="|")
        for row in reader:
            # Assume unique speaker for each utterance
            speaker_id = str(uuid4())
            utt_id, text = row[0].strip(), row[1].strip()
            wav_path = dataset_dir / "wav" / f"{utt_id}.wav"

            yield speaker_id, text, wav_path


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="arabic_speech_corpus.py")
    parser.add_argument("dataset_dir", help="Path to directory with metadata.csv")
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, wav_path in get_metadata(args.dataset_dir):
        writer.writerow((str(wav_path), speaker_id, text))
