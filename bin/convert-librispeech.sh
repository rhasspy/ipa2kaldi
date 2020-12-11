#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts the LibroSpeech dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory as "train-valid-xxx" and execute it.
# Assumes you have GNU parallel and ffmpeg installed.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

metadata_csv="${this_dir}/metadata.csv"

# clip_id | speaker | text
echo 'Gathering metadata...'
find "${this_dir}" -mindepth 3 -name '*.txt' -type f | \
    while read -r text_path; do
        speaker="$(basename "${text_path}" | cut -d'-' -f1)"
        num_lines="$(wc -l < "${text_path}")"
        paste -d'|' \
              <(cut -d' ' -f1 "${text_path}") \
              <(yes "${speaker}" | head -n "${num_lines}") \
              <(cut -d' ' -f2- "${text_path}")
    done > "${metadata_csv}"

# Convert FLAC to WAV
echo 'Converting FLAC files...'
find "${this_dir}" -name '*.flac' -type f | \
    parallel ffmpeg -i {} -acodec pcm_s16le -ar 16000 -ac 1 -f wav "${this_dir}/{/.}.wav"

echo 'Done'
