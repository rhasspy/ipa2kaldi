#!/usr/bin/env bash
set -e

temp_dir="$(mktemp -d)"
function finish {
    rm -rf "${temp_dir}"
}
trap finish EXIT

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

metadata_csv="${this_dir}/metadata.csv"
truncate -s 0 "${metadata_csv}"

todo_path="${temp_dir}/todo"
truncate -s 0 "${todo_path}"

echo 'Gathering metadata...'
find "${this_dir}" -name 'da_mod_*.txt' -type f | \
    while read -r text_path; do
        text_name="$(basename "${text_path}" .txt)"
        text_dir="$(dirname "${text_path}")"
        speaker="$(basename "${text_dir}")"

        dir_num="$(echo "${text_name}" | cut -d'_' -f3)"
        dir_path="$(find "${text_dir}" -maxdepth 1 -type d -name "${dir_num}_*")"

        if [[ -n "${dir_path}" ]]; then
            first_file="$(find "${dir_path}" -name '*.001' -type f | head -n1)"
            if [[ -n "${first_file}" ]]; then
                file_prefix="$(basename "${first_file}" .001)"
                num_files="$(wc -l < "${text_path}")"

                paste -d'|' \
                      <(seq -f '%03g' 1 "${num_files}" | xargs printf "${file_prefix}.%s\n") \
                      <(sed -e 's/\b[0-9]\+\b//g' -e 's/,<komma>/komma/g' -e 's/\.<punktum>/punctum/g' "${text_path}") | \
                    while IFS='|' read -r utt_id text; do
                        raw_path="${dir_path}/${utt_id}"
                        if [[ -f "${raw_path}" ]]; then
                            echo "${utt_id}|${speaker}|${text}" >> "${metadata_csv}"
                            echo "${raw_path}" >> "${todo_path}"
                        else
                            echo "Missing ${raw_path}"
                        fi
                    done

            fi
        fi
    done

echo 'Converting RAW files...'
parallel -a "${todo_path}" sox -t raw -r 22050 -c 1 -B -b 16 -e signed-integer {} -t wav "${this_dir}/{/}.wav"
