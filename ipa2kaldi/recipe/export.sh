#!/usr/bin/env bash
set -e

if [[ -z "$1" ]]; then
    echo "Usage: export.sh dest_directory"
    exit 1
fi

dest_dir="$1"

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"

lm_dir="${this_dir}/lm"
dict_dir="${this_dir}/data/local/dict"
nnet3_dir="${this_dir}/exp/nnet3_chain"
output_dir="${this_dir}/data/output"

# -----------------------------------------------------------------------------

mkdir -p "${dest_dir}"
echo "Exporting to ${dest_dir}"

# Pronunciaton dictionary (lexicon)
echo 'Copying lexicon...'
gzip -9 "${dict_dir}/lexicon.txt" --no-name --to-stdout > "${dest_dir}/base_dictionary.txt.gz"

# ARPA language model
echo 'Copying language model...'
if [[ -f "${lm_dir}/lm.arpa.gz" ]]; then
    zcat "${lm_dir}/lm.arpa.gz" | gzip -9 '-' --no-name --to-stdout > "${dest_dir}/base_language_model.txt.gz"
else
    gzip -9 "${lm_dir}/lm.arpa" --no-name --to-stdout > "${dest_dir}/base_language_model.txt.gz"
fi

# Grapheme to phoneme model
if [[ -f "${output_dir}/g2p.fst" ]]; then
    echo 'Copying g2p model and corpus...'
    gzip -9 "${output_dir}/g2p.fst" --no-name --to-stdout > "${dest_dir}/g2p.fst.gz"
    gzip -9 "${output_dir}/g2p.corpus" --no-name --to-stdout > "${dest_dir}/g2p.corpus.gz"
fi

model_dir="${dest_dir}/acoustic_model"
mkdir -p "${model_dir}"
touch "${model_dir}/path.sh"

# conf/
echo 'Copying conf...'
mkdir -p "${model_dir}/conf"
cp -fL "${this_dir}/conf"/*.conf "${model_dir}/conf"

# extractor/
echo 'Copying extractor...'
mkdir -p "${model_dir}/extractor"
for f in final.dubm final.ie final.mat global_cmvn.stats online_cmvn.conf splice_opts; do
    cp -fL "${nnet3_dir}/extractor/${f}" "${model_dir}/extractor/"
done

# ivectors_test_hires/conf/
echo 'Copying ivectors...'
mkdir -p "${model_dir}/ivectors_test_hires/conf"
cp -fL "${nnet3_dir}/ivectors_test_hires/conf"/*.conf "${model_dir}/ivectors_test_hires/conf/"

# model/
echo 'Copying model...'
mkdir -p "${model_dir}/model"
for f in cmvn_opts den.fst final.mdl normalization.fst tree; do
    cp -fL "${nnet3_dir}/tdnn_250/${f}" "${model_dir}/model/"
done

# phones
echo 'Copying base phones...'
mkdir -p "${model_dir}/phones"
for f in extra_questions.txt nonsilence_phones.txt optional_silence.txt silence_phones.txt; do
    cp -fL "${dict_dir}/${f}" "${model_dir}/phones/"
done

# base graph
echo 'Copying base graph...'
if [[ -d "${model_dir}/base_graph" ]]; then
    rm -rf "${model_dir}/base_graph"
fi

cp -RL "${nnet3_dir}/tdnn_250/graph" "${model_dir}/base_graph"

# -----------------------------------------------------------------------------

echo 'Done'
