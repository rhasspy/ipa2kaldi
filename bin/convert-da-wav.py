#!/usr/bin/env python3
"""Extract WAV file from NST corpus"""
import subprocess
import sys


def main():
    """Main entry point"""
    sample_rate = 16000
    sample_width = 2
    num_channels = 2
    # text = ""

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    input_file = open(input_path, "rb")

    for line in input_file:
        line = line.decode("cp1252").strip()
        if line.lower() == "end_head":
            break

        try:
            field_name, _, field_value = line.split(maxsplit=2)
            # if field_name == "utterance_id":
            #     text = field_value
            if field_name == "sample_coding":
                assert field_value == "pcm", field_value
            elif field_name == "sample_byte_format":
                assert field_value == "01", field_value
            elif field_name == "sample_n_bytes":
                sample_width = int(field_value)
            elif field_name == "sample_rate":
                sample_rate = int(field_value)
            elif field_name == "channel_count":
                num_channels = int(field_value)
        except Exception:
            pass

    # Skip blank lines
    pcm_data = input_file.read()
    data_start = 0
    newline = ord("\n")
    while pcm_data[data_start] == newline:
        data_start += 1

    pcm_data = pcm_data[data_start:]

    # Ensure we're on an even byte
    if (len(pcm_data) % 2) != 0:
        pcm_data = pcm_data[1:]

    proc = subprocess.Popen(
        [
            "sox",
            "-t",
            "raw",
            "-r",
            str(sample_rate),
            "-b",
            str(8 * sample_width),
            "-c",
            str(num_channels),
            "-e",
            "signed-integer",
            "-",
            "-r",
            "16000",
            "-b",
            "16",
            "-c",
            "1",
            "-e",
            "signed-integer",
            "-t",
            "wav",
            output_path,
        ],
        stdin=subprocess.PIPE,
    )
    proc.communicate(input=pcm_data)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
