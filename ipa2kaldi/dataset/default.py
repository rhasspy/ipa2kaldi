"""Loads data from a metadata.csv file with WAV files in the same directory"""
import csv
import typing
from pathlib import Path
from uuid import uuid4


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, wav_path for each item in metadata.csv"""
    metadata_path = dataset_dir / "metadata.csv"
    default_speaker = str(uuid4())

    with open(metadata_path, "r") as metadata_file:
        reader = csv.reader(metadata_file, delim="|")
        for row_index, row in enumerate(reader):
            text = row[0].strip()
            wav_path = dataset_dir / (row[-1].strip() + ".wav")

            if len(row) == 2:
                yield default_speaker, text, wav_path
            elif len(row) == 3:
                speaker = row[1].strip()
                yield speaker, text, wav_path
            else:
                raise ValueError(
                    f"Row {row_index+1} in {metadata_path} has more than 3 columns"
                )
