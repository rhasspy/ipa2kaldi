#!/usr/bin/env bash
set -e

# Augments an audio corpus with noise.
#
# Reads CSV lines with | delmiter and the following fields:
# audio_path|audio_id|txt|[start_ms]|[end_ms]
#
# Outputs CSV in the same format with output audio info.
#
# start_ms and end_ms are optional, and indicate where in audio_path to seek/trim
#
# Noise directory has the following structure
# _background_/
#   <long WAV files>
# LABEL1/
#   <short WAV files>
# LABEL2/
#   <short WAV files>
#
# where LABEL1 and LABEL2 are Kaldi "words" like SIL, NSN, or SPN.
#
# Background WAV files in _background_ are automatically trimmed to fit
# foreground audio. Other WAV files are *not* trimmed, so they shouldn't be more
# than a few seconds long.
#
# Credit: https://github.com/gooofy/zamia-speech/blob/master/speech_gen_noisy.py
#
# Set stride externally with: awk 'NR % stride == 0'

if [[ -z "$2" ]]; then
    echo 'Usage: add_noise.sh output_dir noise_dir < CSV > CSV'
    exit 1
fi

output_dir="$1"
noise_dir="$2"
shift 2

# Directory with long background WAV files
bg_dir="${noise_dir}/_background_"
if [[ ! -d "${bg_dir}" ]]; then
    echo "Missing ${bg_dir}"
    exit 1
fi

# Directories with foreground audio (SIL, NSN, etc.)
fg_labels=()
while read -r dir_name; do
    label="$(basename "${dir_name}")"
    fg_labels+=("${label}")
done < <(find "${noise_dir}" -mindepth 1 -maxdepth 1 -not -name '_*')

if [[ -z "${fg_labels[@]}" ]]; then
    echo "No foreground dirs found in ${noise_dir}"
    exit 1
fi

mkdir -p "${output_dir}"

# -----------------------------------------------------------------------------

# Use a temporary directory, and clean it up on exit
# temp_dir="$(mktemp -d)"
# function cleanup {
#     rm -rf "${temp_dir}"
# }

# trap cleanup EXIT
temp_dir="test"

# -----------------------------------------------------------------------------

# # Gather paths to all background WAV files
# find "${bg_dir}" -name '*.wav' -type f > "${temp_dir}/bg.txt"

# # Gather labels for and paths to all foreground WAV files
# rm -f "${temp_dir}/fg.txt"
# for fg_label in "${fg_labels[@]}"; do
#     while read -r fg_path; do
#         echo "${fg_label} ${fg_path}"
#     done < <(find "${noise_dir}/${fg_label}" -name '*.wav' -type f) \
#          >> "${temp_dir}/fg.txt"
# done

# # Cache WAV lengths of all noise files
# echo "Computing lengths of WAV file(s) in ${noise_dir}" >&2
# find "${noise_dir}" -name '*.wav' -type f | \
#         parallel "mkdir -p ${temp_dir}/stats/{//} && sox {} -n stat > ${temp_dir}/stats/{}_stats.txt 2>&1 && grep -i length ${temp_dir}/stats/{}_stats.txt | cut -d: -f2 > ${temp_dir}/stats/{}_length.txt"

# -----------------------------------------------------------------------------

function augment_wav {
    job_num="$1"
    temp_dir="$2"
    output_dir="$3"

    # Read line of CSV with | delimiter
    while IFS='|' read -r audio_path audio_id text start_ms end_ms; do
        # Get random audio settings
        fg_level=-$((${RANDOM} % 101))  # (-100, 0)
        fg_level="$(echo "scale=2;${fg_level}/100" | bc)"  # (-1, 0)

        reverb=$((${RANDOM} % 51))  # [0,50]
        bg_level=-$((10 + ${RANDOM} % 16))  # -15,-10

        # Convert and trim input audio
        ffmpeg_args=('-loglevel' 'panic' '-y' '-i' "${audio_path}")

        if [[ -n "${start_ms}" ]]; then
            # Seek
            # -ss <seconds>
            ffmpeg_args+=('-ss' "$(echo "scale=6;${start_ms}/1000" | bc | xargs printf '%0.6f')")
        fi

        if [[ -n "${end_ms}" ]]; then
            # Trim
            # -t <seconds>
            duration_ms=$((${end_ms} - ${start_ms}))
            ffmpeg_args+=('-t' "$(echo "scale=6;${duration_ms}/1000" | bc | xargs printf '%0.6f')")
        fi

        ffmpeg_args+=('-ar' '16000' '-ac' '1' '-acodec' 'pcm_s16le' '-f' 'wav')

        input_wav="$(mktemp "--tmpdir=${temp_dir}" --suffix=.wav)"
        ffmpeg "${ffmpeg_args[@]}" "${input_wav}"

        # Get length of input audio
        input_stats="$(mktemp "--tmpdir=${temp_dir}" --suffix=.txt)"
        sox "${input_wav}" -n stat > "${input_stats}" 2>&1
        input_length="$(grep -i length "${input_stats}" | cut -d: -f2)"

        # Choose random background WAV
        bg="$(shuf -n1 "${temp_dir}/bg.txt")"
        bg_length="$(cat "${temp_dir}/stats/${bg}_length.txt")"

        # Choose two random foreground WAVs
        read -r fg1_label fg1 < <(shuf -n1 "${temp_dir}/fg.txt")
        fg1_length="$(cat "${temp_dir}/stats/${fg1}_length.txt")"

        read -r fg2_label fg2 < <(shuf -n1 "${temp_dir}/fg.txt")
        fg2_length="$(cat "${temp_dir}/stats/${fg2}_length.txt")"

        # Total length of foreground audio.
        # Includes [noise] [spoken audio] [noise]
        fg_length="$(echo "${fg1_length}+${input_length}+${fg2_length}" | bc)"

        # Get offset into background noise file.
        # Use /1 to get floor
        max_bg_offset="$(echo "(${bg_length}-${fg_length})/1" | bc)"
        bg_offset=$((${RANDOM} % (${max_bg_offset}+1)))

        # Create output WAV
        output_id="${audio_id}_noisy_${job_num}"
        output_wav="${output_dir}/${output_id}.wav"

        # Mix foreground and background.
        # Normalize and add reverb.
        sox -b 16 -r 16000 -c 1 \
            --combine mix \
            -t wav <(sox --norm="${fg_level}" "${fg1}" "${input_wav}" "${fg2}" -t wav - compand 0.01,0.2 -90,-10 -5 reverb "${reverb}" 2>/dev/null) \
            -t wav <(sox --norm="${bg_level}" "${bg}" -t wav - trim "${bg_offset}" "${fg_length}" 2>/dev/null) \
            -t wav "${output_wav}" \
            2>/dev/null

        # Example: NSN ...(transcription)... SPN
        text="${fg1_label} ${text} ${fg2_label}"

        # Output CSV line with | delimiter
        echo "${output_wav}|${output_id}|${text}"
    done
}

export -f augment_wav

# -----------------------------------------------------------------------------

parallel "$@" -n1 --pipe augment_wav '{#}' "${temp_dir}" "${output_dir}"
