#!/usr/bin/env bash
set -e

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

metadata="${this_dir}/metadata.csv"
truncate -s 0 "${metadata}"

find "${this_dir}" -mindepth 1 -maxdepth 1 -type d | \
    while read -r dir_path; do
        dir_name="$(basename "${dir_path}")"
        # Extract metadata
        find "${dir_path}" -name '*.wav' -type f | \
            parallel "${this_dir}/extract-da-text.py" "${dir_name}_" {} \
                     >> "${metadata}"


        # Convert WAV files
        # find "${dir_path}" -name '*.wav' -type f | \
        #     parallel "${this_dir}/convert-da-wav.py" {} "${this_dir}/${dir_name}_{/}"
    done
