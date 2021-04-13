#!/usr/bin/env python3
"""
Converts Tunisian MSA dataset
"""
import argparse
import csv
import json
import sys
import typing
from pathlib import Path


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from mls dataset"""
    speech_dir = dataset_dir / "speech" / "train"
    transcripts_dir = dataset_dir / "transcripts" / "train"

    # Load answers
    answers_tsv_path = transcripts_dir / "answers.tsv"
    with open(answers_tsv_path, "r") as answers_tsv_file:
        answers_tsv = csv.reader(answers_tsv_file, delimiter="\t")
        for row in answers_tsv:
            # CTELLTWO_23_Answers_Arabic_20
            file_id_parts = row[0].strip().split("_", maxsplit=4)
            text = row[1].strip()

            group_id = file_id_parts[0]
            speaker_id = file_id_parts[1]
            utt_num = file_id_parts[-1]

            wav_path = (
                speech_dir / group_id / "Answers_Arabic" / speaker_id / f"{utt_num}.wav"
            )

            yield speaker_id, text, wav_path

    # num -> text
    recording_texts: typing.Dict[str, str] = {}

    # Load recordings
    recordings_tsv_path = transcripts_dir / "recordings.tsv"
    with open(recordings_tsv_path, "r") as recordings_tsv_file:
        recordings_tsv = csv.reader(recordings_tsv_file, delimiter="\t")
        for row in recordings_tsv:
            recording_num = row[0].strip()
            text = row[1].strip()
            recording_texts[recording_num] = text

    for group_dir in speech_dir.iterdir():
        if not group_dir.is_dir():
            continue

        recordings_dir = group_dir / "Recordings_Arabic"
        for speaker_dir in recordings_dir.iterdir():
            if not speaker_dir.is_dir():
                continue

            speaker_id = speaker_dir.name
            for wav_path in speaker_dir.glob("*.wav"):
                recording_num = wav_path.stem
                text = recording_texts[recording_num]
                yield speaker_id, text, wav_path


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="tunisian_msa.py")
    parser.add_argument(
        "dataset_dir", help="Path to directory with speech/transcripts directories"
    )
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, wav_path in get_metadata(args.dataset_dir):
        writer.writerow((str(wav_path), speaker_id, text))
