"""
Converts Mozilla Common Voice datasets
"""
import csv
import typing
from pathlib import Path


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from Common Voice dataset"""
    validated_path = dataset_dir / "validated.tsv"
    clips_dir = dataset_dir / "clips"

    with open(validated_path, "r") as validate_file:
        reader = csv.reader(validate_file, delimiter="\t")
        for row in reader:
            speaker_id = row[0].strip()
            mp3_path = clips_dir / row[1].strip()
            text = row[2].strip()

            yield speaker_id, text, mp3_path
