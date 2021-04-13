#!/usr/bin/env python3
"""
Converts the Arabic Speech Corpus for Isolated Words
http://www.cs.stir.ac.uk/~lss/arabic/
"""
import argparse
import csv
import json
import sys
import typing
from pathlib import Path

_WORDS = {
    1: "صفر",
    2: "واحد",
    3: "إثنان",
    4: "ثلاثة",
    5: "أربعة",
    6: "خمسة",
    7: "ستة",
    8: "سبعة",
    9: "ثمانية",
    10: "تسعة",
    11: "التنشيط",
    12: "التحويل",
    13: "الرصيد",
    14: "التسديد",
    15: "نعم",
    16: "لا",
    17: "التمويل",
    18: "البيانات",
    19: "الحساب",
    20: "إنهاء",
}


def get_metadata(dataset_dir: Path) -> typing.Iterable[typing.Tuple[str, str, Path]]:
    """Load speaker, text, audio path dataset"""
    for wav_path in dataset_dir.glob("*.wav"):
        wav_id_parts = wav_path.stem.split(".", maxsplit=2)
        speaker_id = wav_id_parts[0]
        word_id = int(wav_id_parts[2])
        text = _WORDS[word_id]

        yield (speaker_id, text, wav_path)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="arabic_isolated_words.py")
    parser.add_argument("dataset_dir", help="Path to directory with WAV files")
    parser.add_argument("--delimiter", default="|", help="Output CSV deliminter")
    args = parser.parse_args()

    args.dataset_dir = Path(args.dataset_dir)

    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    for speaker_id, text, wav_path in get_metadata(args.dataset_dir):
        writer.writerow((str(wav_path), speaker_id, text))
