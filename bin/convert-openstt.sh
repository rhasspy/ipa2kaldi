#!/usr/bin/env bash
set -e

# -----------------------------------------------------------------------------
# Converts an OpenSTT Rhasspy's ipa2kaldi format.
#
# Put this script in the top-level directory execute it.
# Assumes you have GNU parallel and ffmpeg installed.
# -----------------------------------------------------------------------------

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

metadata_csv="${this_dir}/metadata.csv"

echo 'Collecting metadata...'
collection="$(basename "${this_dir}")"

temp_file="$(mktemp)"
function finish {
    rm -f "${temp_file}"
}
trap finish EXIT

find "${this_dir}" -mindepth 2 -name '*.opus' > "${temp_file}"

# clip_id | speaker | text
paste -d'|' \
      <(cat "${temp_file}" | xargs -I{} basename {} .opus | xargs -I{} printf "${collection}_%s\n" {}) \
      <(cat "${temp_file}" | xargs dirname | xargs dirname | xargs -I{} basename {} | xargs -I{} printf "${collection}_%s\n" {}) \
      <(cat "${temp_file}" | sed -e 's/.opus$/.txt/' | xargs cat) \
      > "${metadata_csv}"

# Convert OPUS to WAV
echo 'Converting OPUS files...'
cat "${temp_file}" |
    parallel ffmpeg -i {} -acodec pcm_s16le -ar 16000 -ac 1 -f wav "${this_dir}/${collection}_{/.}.wav"
