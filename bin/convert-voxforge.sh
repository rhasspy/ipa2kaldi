#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts a Voxforge dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory all of the speaker directories and
# execute it.
# Assumes WAV files are already 16-bit 16Khz mono
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

# Collect all metadata
echo 'Collecting metadata...'
metadata_csv="${this_dir}/metadata.csv"
truncate -s 0 "${metadata_csv}"

find "${this_dir}" -type f -iname 'prompts-original' | \
    while read -r fname; do
        prompts_dir="$(dirname "${fname}")"
        speaker_dir="$(dirname "${prompts_dir}")"
        speaker="$(basename "${speaker_dir}")"

        num_lines="$(wc -l < "${fname}")"

        # clip_id | speaker | text
        paste -d'|' \
              <(cut -d' ' -f1 "${fname}" | xargs -n1 printf '%s_%s\n' "${speaker}") \
              <(yes "${speaker}" | head -n "${num_lines}") \
              <(cut -d' ' -f2- "${fname}") \
              >> "${metadata_csv}"
    done

# Symlink all WAV files into one directory
echo 'Symlinking WAV files...'
find "${this_dir}" -mindepth 2 -type f -name '*.wav' | \
    while read -r fname; do
        wav_dir="$(dirname "${fname}")"
        speaker_dir="$(dirname "${wav_dir}")"
        speaker="$(basename "${speaker_dir}")"

        link_name="${speaker}_$(basename "${fname}")"
        ln -sf "${fname}" "${this_dir}/${link_name}"
    done

echo 'Done'
