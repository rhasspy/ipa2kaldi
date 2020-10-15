#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts an M-AILabs dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory as "by_book" and execute it.
# Assumes WAV files are 16-bit 16Khz mono already.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

# Collect all metadata
echo 'Collecting metadata..'
metadata_csv="${this_dir}/metadata.csv"
truncate -s 0 "${metadata_csv}"

find "${this_dir}/by_book" -type f -name 'metadata.csv' | \
    while read -r fname; do
        meta_dir="$(dirname "${fname}")"
        book="$(basename "${meta_dir}")"
        book_dir="$(dirname "${meta_dir}")"
        speaker="$(basename "${book_dir}")"

        num_lines="$(wc -l < "${fname}")"

        # clip_id | speaker | text
        paste -d'|' \
                  <(cut -d'|' -f1 "${fname}") \
                  <(yes "${speaker}" | head -n "${num_lines}") \
                  <(cut -d'|' -f3- "${fname}") \
                  >> "${metadata_csv}"
    done

# Symlink all WAV files into one directory
echo 'Symlinking WAV files...'
find "${this_dir}/by_book" -type f -name '*.wav' -print0 | \
    xargs -0 ln -sf -t "${this_dir}"

echo 'Done'
