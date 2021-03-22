#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts the LJSpeech dataset to Rhasspy's ipa2kaldi format.
# https://keithito.com/LJ-Speech-Dataset/
#
# Put this script in the same directory as "metadata.csv" and execute it.
# Assumes WAV files are 16-bit 22.5Khz mono already.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

old_metadata_csv="${this_dir}/metadata.old.csv"
metadata_csv="${this_dir}/metadata.csv"

if [[ ! -f "${old_metadata_csv}" ]]; then
    mv "${metadata_csv}" "${old_metadata_csv}"
    cut -d'|' -f1,3 < "${old_metadata_csv}" > "${metadata_csv}"
fi

# Symlink all WAV files into one directory
echo 'Symlinking WAV files...'
find "${this_dir}/wavs" -type f -name '*.wav' -print0 | \
    xargs -0 ln -sf -t "${this_dir}"

echo 'Done'
