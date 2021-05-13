#!/usr/bin/env bash
set -e

# Augments an audio corpus with noise.
#
# Credit: https://github.com/gooofy/zamia-speech/blob/master/speech_gen_noisy.py

if [[ -z "$4" ]]; then
    echo 'Usage: add_noise.sh input_audio fg1 fg2 bg [bg_offset] [bg_duration] [fg_offset=] [fg_duration=] [fg_level=0] [bg_level=0] [reverb=0]'
    exit 1
fi

input_audio="$1"
fg1="$2"
fg2="$3"
bg="$4"
bg_offset="$5"
bg_duration="$6"
fg_offset="$7"
fg_duration="$8"
fg_level="${9:-0}"
bg_level="${10:-0}"
reverb="${11:-0}"

# -----------------------------------------------------------------------------

ffmpeg_args=()
if [[ -n "${fg_offset}" ]]; then
    ffmpeg_args+=('-ss' "${fg_offset}")
fi

if [[ -n "${fg_duration}" ]]; then
    ffmpeg_args+=('-t' "${fg_duration}")
fi

bg_args=()
if [[ -n "${bg_offset}" ]]; then
    bg_args+=('trim' "${bg_offset}")

    if [[ -n "${bg_duration}" ]]; then
        bg_args+=("${bg_duration}")
    fi
fi

# -----------------------------------------------------------------------------

temp_wav="$(mktemp --suffix=.wav)"
function cleanup {
    rm -f "${temp_wav}"
}
trap cleanup EXIT

# -----------------------------------------------------------------------------

ffmpeg -y -i "${input_audio}" "${ffmpeg_args[@]}" -ar 16000 -ac 1 -acodec pcm_s16le -f wav - | \
    sox "--norm=${fg_level}" \
        "${fg1}" \
        -t wav --ignore-length - \
        "${fg2}" \
        -p \
        compand 0.01,0.2 -90,-10 -5 reverb "${reverb}" | \
    sox -b 16 -r 16000 -c 1 \
        --combine mix \
        -t sox - \
        -t sox <(sox "--norm=${bg_level}" "${bg}" -p "${bg_args[@]}") \
        -t wav "${temp_wav}"

cat "${temp_wav}"
