#!/usr/bin/env python3
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pydub import AudioSegment

_DIR = Path(".").absolute()


def main():
    metadata_path = _DIR / "metadata.csv"
    with open(metadata_path, "w") as metadata_file:
        metadata_writer = csv.writer(metadata_file, delimiter="|")

        article_name = _DIR.name
        swc_path = _DIR / "aligned.swc"
        ogg_path = _DIR / "audio.ogg"

        print("Loading audio from", ogg_path)
        audio = AudioSegment.from_ogg(ogg_path)

        print("Parsing alignments from", swc_path)
        article = ET.parse(swc_path)
        sentence_num = 1

        for s_elem in article.findall(".//s"):
            start_ms = None
            end_ms = None
            tokens = []
            for n_elem in s_elem.findall(".//n"):
                tokens.append(n_elem.attrib["pronunciation"])

                if "start" in n_elem.attrib:
                    n_start_ms = int(n_elem.attrib["start"])
                    n_end_ms = int(n_elem.attrib["end"])

                    if (start_ms is None) or (n_start_ms < start_ms):
                        start_ms = n_start_ms

                    if (end_ms is None) or (n_end_ms > end_ms):
                        end_ms = n_end_ms

            for ph_elem in s_elem.findall(".//ph"):
                if "start" in ph_elem.attrib:
                    ph_start_ms = int(ph_elem.attrib["start"])
                    ph_end_ms = int(ph_elem.attrib["end"])

                    if (start_ms is None) or (ph_start_ms < start_ms):
                        start_ms = ph_start_ms

                    if (end_ms is None) or (ph_end_ms > end_ms):
                        end_ms = ph_end_ms

            if tokens and (start_ms is not None) and (end_ms is not None):
                utt_id = f"{article_name}_{sentence_num}"
                text = " ".join(tokens)
                metadata_writer.writerow((utt_id, text))

                sentence_segment = audio[start_ms:end_ms]
                sentence_path = _DIR / f"{utt_id}.wav"
                sentence_segment.export(
                    sentence_path, format="wav", parameters=["-ar", "16000", "-ac", "1"]
                )

                print(utt_id, text, sentence_path)
                sentence_num += 1


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
