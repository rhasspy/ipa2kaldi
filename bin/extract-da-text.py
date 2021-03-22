#!/usr/bin/env python3
import os
import sys


def main():
    """Main entry point"""
    prefix = sys.argv[1]
    input_path = sys.argv[2]

    text = ""
    file_name = ""

    with open(input_path, "rb") as input_file:
        for line in input_file:
            line = line.decode("cp1252").strip()
            if line.lower() == "end_head":
                break

            try:
                field_name, _, field_value = line.split(maxsplit=2)
                if field_name == "utterance_id":
                    text = field_value
                elif field_name == "speech_file_name":
                    file_name = field_value
            except Exception:
                pass

        utterance_id = os.path.splitext(file_name)[0]
        print(prefix + utterance_id, text, sep="|")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
