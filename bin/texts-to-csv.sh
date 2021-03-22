#!/usr/bin/env bash
echo 'Reading text file names from stdin...' >&2

while read -r file_path; do
    utt_id="$(basename "${file_path}" .txt)"
    text="$(cat "${file_path}")"
    printf '%s|%s\n' "${utt_id}" "${text}"
done
