"""
Converts M-AILabs datasets
"""
import argparse
import csv
import json
import sys
import typing
from pathlib import Path


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from m-ai labs dataset"""
    by_book_dir = dataset_dir / "by_book"

    # Handle directories with known speakers
    for known_speaker in ["female", "male"]:
        known_speaker_dir = by_book_dir / known_speaker
        if not known_speaker_dir.is_dir():
            continue

        # by_book/<gender>/<speaker>/<book>
        for speaker_dir in known_speaker_dir.iterdir():
            if not speaker_dir.is_dir():
                continue

            speaker_id = speaker_dir.name
            for book_dir in speaker_dir.iterdir():
                if not book_dir.is_dir():
                    continue

                for text, wav_path in _load_metadata(book_dir):
                    yield speaker_id, text, wav_path

    # Handle directories with unknown/mixed speakers
    for unknown_speaker in ["mix"]:
        unknown_speaker_dir = by_book_dir / unknown_speaker
        if not unknown_speaker_dir.is_dir():
            continue

        # by_book/mix/<book>
        utt_idx = 0
        for book_dir in unknown_speaker_dir.iterdir():
            if not book_dir.is_dir():
                continue

            # Assume each utterance is from a unique speaker
            for text, wav_path in _load_metadata(book_dir):
                speaker_id = "speaker_{utt_idx}"
                yield speaker_id, text, wav_path
                utt_id += 1


def _load_metadata(book_dir: Path) -> typing.Iterable[typing.Tuple[str, Path]]:
    """Yield text, wav path from metadata for book"""
    metadata_csv = book_dir / "metadata.csv"
    wav_dir = book_dir / "wavs"

    if metadata_csv.is_file():
        # Load CSV metadata
        with open(metadata_csv, "r") as metadata_file:
            reader = csv.reader(metadata_file, delimiter="|")
            for row in reader:
                utt_id, clean_text = row[0].strip(), row[2].strip()
                wav_path = wav_dir / f"{utt_id}.wav"

                yield (clean_text, wav_path)
    else:
        # Load JSON metadata
        metadata_json = book_dir / "metadata_mls.json"
        if metadata_json.is_file():
            with open(metadata_json, "r") as metadata_file:
                metadata = json.load(metadata_file)
                for wav_name, utt_info in metadata.items():
                    wav_path = wav_dir / wav_name
                    clean_text = metadata["clean"].strip()
                    yield (clean_text, wav_path)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="m_ailabs.py")
    parser.add_argument("dataset_dir", help="Path to directory with by_book directory")
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, wav_path in get_metadata(args.dataset_dir):
        writer.writerow((str(wav_path), speaker_id, text))
