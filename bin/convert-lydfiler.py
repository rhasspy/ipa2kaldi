#!/usr/bin/env python3
"""Extract metadata from NST corpus"""
import json
import os
import sys
from pathlib import Path

_DIR = Path(__file__).parent


def main():
    """Main entry point"""
    json_path = Path(sys.argv[1])
    with open(json_path, "r") as json_file:
        info = json.load(json_file)

    wav_dir = _DIR / "se" / info["pid"]
    assert wav_dir.is_dir(), f"Missing directory {wav_dir}"

    for recording in info["val_recordings"]:
        text = recording["text"]
        if text.startswith("("):
            # Skip ( ... tyst under denna inspelning ...)
            continue

        wav_path = wav_dir / (
            wav_dir.name + "_" + os.path.splitext(recording["file"])[0] + "-1.wav"
        )
        assert wav_path.is_file(), f"Missing file {wav_path}"
        utterance_id = wav_path.stem
        print(utterance_id, text, sep="|")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
