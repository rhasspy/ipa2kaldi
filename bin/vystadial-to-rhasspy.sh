#!/usr/bin/env bash
set -e

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

data="${this_dir}/data"
metadata_csv="${this_dir}/metadata.csv"

# Move WAV files here
echo 'Moving WAV files...'
find "${data}" -type f -name '*.wav' -exec mv '{}' "${this_dir}/" \;

# Gather transcripts into "csv" file.
# Assume each WAV file is a unique speaker.
#
# clip_id | speaker | text
truncate -s 0 "${metadata_csv}"

echo 'Writing transcripts...'
for text_file in "${data}/"*.trn;
do
    clip_id="$(basename ${text_file} .wav.trn)"
    speaker="${clip_id}"
    text="$(cat ${text_file})"

    if [[ "${text}" == '_NOISE_' ]]; then
        echo "Skipping ${clip_id} (noise)" >&2
    else
        printf '%s|%s|%s\n' "${clip_id}" "${speaker}" "${text}" >> "${metadata_csv}"
    fi
done

echo 'Done'
