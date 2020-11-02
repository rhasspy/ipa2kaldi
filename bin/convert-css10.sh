#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts a css10 dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in next to the transcript.txt.
# Converts WAV files to 16-bit 16Khz mono.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

metadata_csv="${this_dir}/metadata.csv"

speaker="$(basename "${this_dir}")"
transcript="${this_dir}/transcript.txt"

num_lines="$(wc -l < "${transcript}")"

# clip_id | speaker | text
echo 'Gathering metadata'
paste -d'|' \
      <(cut -d'|' -f1 "${transcript}" | sed -e 's|^.\+/||' | sed -e 's/\.wav$//') \
      <(yes "${speaker}" | head -n "${num_lines}") \
      <(cut -d'|' -f2 "${transcript}") \
      > "${metadata_csv}"

# -----------------------------------------------------------------------------

temp_file="$(mktemp)"
function cleanup {
    rm -f "${temp_file}"
}

trap cleanup EXIT

cut -d'|' -f2 "${metadata_csv}" | sort | uniq | \
    while read -r speaker; do
        find "${speaker}/" -type f -name '*.wav'
    done >> "${temp_file}"

# -----------------------------------------------------------------------------

echo 'Converting WAV files...'
parallel sox "{}" -r 16000 -e signed-integer -b 16 -c 1 -t wav "${this_dir}/{/}" < "${temp_file}"

echo 'Done'
