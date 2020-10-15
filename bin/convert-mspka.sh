#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts the MSPKA dataset to Rhasspy's ipa2kaldi format.
#
# Put this script in the same directory all of the speaker directories and
# execute it.
# Assumes you have GNU parallel and sox installed.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

# Collect all metadata
echo 'Collecting metadata...'
metadata_csv="${this_dir}/metadata.csv"
truncate -s 0 "${metadata_csv}"

find "${this_dir}" -type f -name 'list_sentences' | \
    while read -r fname; do
        fdir="$(dirname "${fname}")"
        IFS='_' read -ra speaker_version <<< "$(basename ${fdir})"
        speaker="${speaker_version[0]}"
        version="${speaker_version[1]}"

        wav_dir="${fdir}/wav_${version}"
        num_lines="$(wc -l < ${fname})"

        # clip_id | speaker | text
        paste -d'|' \
              <(cut -d')' -f1 "${fname}" | xargs -n1 printf '%s_%s\n' "${speaker}") \
              <(yes "${speaker}" | head -n "${num_lines}") \
              <(cut -d')' -f2- "${fname}" | sed -e 's/^ //') \
              >> "${metadata_csv}"
    done

# Convert WAV files
echo 'Converting WAV files...'
find "${this_dir}" -mindepth 2 -type f -name '*.wav' | \
    parallel sox "{}" -r 16000 -e signed-integer -b 16 -c 1 -t wav "${this_dir}/{/}"

echo 'Done'
