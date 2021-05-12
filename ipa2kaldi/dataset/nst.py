#!/usr/bin/env python3
"""
Converts lydfiler_16_1 dataset
Audio: https://www.nb.no/sbfil/talegjenkjenning/16kHz_2020/dk_2020/lydfiler_16_1.tar.gz
JSON: https://www.nb.no/sbfil/talegjenkjenning/16kHz_2020/se_2020/ADB_SWE_0467.tar.gz
"""
import json
import logging
import os
import typing
from pathlib import Path
from uuid import uuid4

_LOGGER = logging.getLogger("ipa2kaldi.dataset.nst")


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from Swedish NST dataset (reorganized)"""
    json_dir = dataset_dir / "json"
    for json_path in json_dir.glob("*.json"):
        with open(json_path, "r") as json_file:
            info = json.load(json_file)

        speaker_id = info.get("Speaker_ID", "").strip()
        if not speaker_id:
            speaker_id = str(uuid4())

        wav_dir = dataset_dir / "se" / info["pid"]
        if not wav_dir.is_dir():
            _LOGGER.warning("Missing directory %s", wav_dir)
            continue

        for recording in info["val_recordings"]:
            text = recording["text"]
            if text.startswith("("):
                # Skip ( ... tyst under denna inspelning ...)
                continue

            # Use channel 1
            wav_path = wav_dir / (
                wav_dir.name + "_" + os.path.splitext(recording["file"])[0] + "-1.wav"
            )

            if not wav_path.is_file():
                _LOGGER.warning("Missing file %s", wav_path)
                continue

            yield speaker_id, text, wav_path
