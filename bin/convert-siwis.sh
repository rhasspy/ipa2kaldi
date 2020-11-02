#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts the SIWIS dataset to Rhasspy's ipa2kaldi format.
#
# Put this script next to the "wavs" directory.
# Converts WAV files to 16-bit 16Khz mono.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

speaker='siwis'
metadata_csv="${this_dir}/metadata.csv"

echo 'Collecting metadata..'
while read -r text_file;
do
    utt_id="$(basename "${text_file}" .txt)"
    text="$(cat "text/${text_file}")"
    printf '%s|%s|%s\n' "${utt_id}" "${speaker}" "${text}"
done <"${this_dir}/lists/all_text.list" > "${metadata_csv}"

echo 'Converting WAV files...'
find "${this_dir}/wavs" -type f -name '*.wav' | \
    parallel sox "{}" -r 16000 -e signed-integer -b 16 -c 1 -t wav "${this_dir}/{/}"

echo 'Done'
