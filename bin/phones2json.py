#!/usr/bin/env python3
import json
import sys


def main():
    utt_id = None
    prons = []

    def output_latest():
        if utt_id:
            json.dump(
                {"utt_id": utt_id, "prons": prons}, sys.stdout, ensure_ascii=False
            )
            print("")

    for line in sys.stdin:
        parts = line.strip().split()
        if parts[0] != utt_id:
            output_latest()
            utt_id = parts[0]
            prons = []

        prons.append(
            {
                "start_frame": int(parts[1]),
                "num_frames": int(parts[2]),
                "word": parts[3],
                "phones": [p.split("_")[0] for p in parts[4:]],
            }
        )


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
