#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts a Mozilla Common Voice dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory as "validated.tsv" and execute it.
# Assumes you have GNU parallel and ffmpeg installed.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

clips="${this_dir}/clips"
validated_tsv="${this_dir}/validated.tsv"

metadata_csv="${this_dir}/metadata.csv"

# clip_id | speaker | text
paste -d'|' \
      <(tail -n +2 "${validated_tsv}" | cut -d$'\t' -f2 | xargs -I{} -n1 basename '{}' .mp3) \
      <(tail -n +2 "${validated_tsv}" | cut -d$'\t' -f1) \
      <(tail -n +2 "${validated_tsv}" | cut -d$'\t' -f3) \
      > "${metadata_csv}"

# Convert MP3 to WAV
cut -d'|' -f1 "${metadata_csv}" | \
    parallel ffmpeg -i "${clips}/{0}.mp3" -acodec pcm_s16le -ar 16000 -ac 1 -f wav "${this_dir}/{0}.wav"
