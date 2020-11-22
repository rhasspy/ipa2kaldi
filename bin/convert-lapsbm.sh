#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts the LapsBM dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory as all of the speaker directories and
# execute it.
# Assumes you have GNU parallel and sox installed.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

# Collect all metadata
echo 'Collecting metadata...'
metadata_csv="${this_dir}/metadata.csv"
truncate -s 0 "${metadata_csv}"

find "${this_dir}" -maxdepth 1 -mindepth 1 -type d | \
    while read -r dpath; do
        dname="$(basename "${dpath}")"
        speaker="$(echo "${dname}" | sed -e 's/^[^-]\+-//')"

        find "${dpath}" -type f -name '*.wav' | \
            while read -r wavpath; do
                clip_id="$(basename "${wavpath}" .wav)"
                text="$(cat "${dpath}/${clip_id}.txt")"

                # clip_id | speaker | text
                printf '%s|%s|%s\n' "${clip_id}" "${speaker}" "${text}"
            done >> "${metadata_csv}"
    done

# Convert WAV files
echo 'Converting WAV files...'
find "${this_dir}" -mindepth 2 -type f -name '*.wav' | \
    parallel sox "{}" -r 16000 -e signed-integer -b 16 -c 1 -t wav "${this_dir}/{/}"

echo 'Done'
