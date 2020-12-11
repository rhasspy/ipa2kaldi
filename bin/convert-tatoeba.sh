#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts Tatoeba dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory as "sentences_with_audio.csv" and
# execute it.
# Assumes you have GNU parallel and ffmpeg installed.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

sentences_tsv="${this_dir}/sentences_with_audio.csv"
metadata_csv="${this_dir}/metadata.csv"

echo 'Gathering metadata...'

# clip_id | speaker | text
paste -d'|' \
      <(tail -n +2 "${sentences_tsv}" | cut -d$'\t' -f1) \
      <(tail -n +2 "${sentences_tsv}" | cut -d$'\t' -f2) \
      <(tail -n +2 "${sentences_tsv}" | cut -d$'\t' -f3) \
      > "${metadata_csv}"

# Convert MP3 to WAV
find "${this_dir}" -mindepth 2 -name '*.mp3' -type f | \
    parallel ffmpeg -i {} -acodec pcm_s16le -ar 16000 -ac 1 -f wav "${this_dir}/{/.}.wav"

echo 'Done'
