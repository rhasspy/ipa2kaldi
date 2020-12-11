#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts the VCTK dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory as the "txt" directory.
# Assumes you have GNU parallel and ffmpeg installed.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

metadata_csv="${this_dir}/metadata.csv"

# clip_id | speaker | text
echo 'Gathering metadata...'
find "${this_dir}/txt" -name '*.txt' -type f | \
    while read -r text_path; do
        clip_id="$(basename "${text_path}" .txt)"
        speaker="$(dirname "${text_path}" | xargs basename)"
        text="$(cat "${text_path}")"
        printf '%s|%s|%s\n' "${clip_id}" "${speaker}" "${text}"
    done > "${metadata_csv}"

# Convert FLAC to WAV
echo 'Converting FLAC files...'
find "${this_dir}" -name '*.flac' -type f | \
    parallel ffmpeg -i {} -acodec pcm_s16le -ar 16000 -ac 1 -f wav "${this_dir}/{/.}.wav"

echo 'Done'
