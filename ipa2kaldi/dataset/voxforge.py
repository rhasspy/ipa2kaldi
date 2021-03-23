"""
Converts VoxForge datasets
"""
import argparse
import csv
import json
import sys
import typing
from pathlib import Path


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path from voxforge dataset"""
    # <speaker>/etc/prompts-original
    # <speaker>/wav
    for speaker_dir in dataset_dir.iterdir():
        if not speaker_dir.is_dir():
            continue

        speaker_id = speaker_dir.name
        prompts_path = speaker_dir / "etc" / "prompts-original"
        wav_dir = speaker_dir / "wav"

        prompt_encoding = "utf-8"
        for encoding in ["utf-8", "cp1252", "ascii"]:
            try:
                with open(prompts_path, "r", encoding=encoding) as prompts_file:
                    for line in prompts_file:
                        pass

                # Made it all the way through
                prompt_encoding = encoding
                break
            except UnicodeDecodeError:
                # Wrong encoding
                pass

        # Open for real
        with open(prompts_path, "r", encoding=prompt_encoding) as prompts_file:
            for line in prompts_file:
                line = line.strip()
                if not line:
                    continue

                utt_id, text = line.split(maxsplit=1)
                wav_path = wav_dir / f"{utt_id}.wav"

                yield (speaker_id, text.strip(), wav_path)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="m_ailabs.py")
    parser.add_argument(
        "dataset_dir", help="Path to directory with speaker directories"
    )
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, wav_path in get_metadata(args.dataset_dir):
        writer.writerow((str(wav_path), speaker_id, text))
