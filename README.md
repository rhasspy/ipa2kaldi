# ipa2kaldi

Creates a [Kaldi nnet3 recipe](https://kaldi-asr.org/doc/dnn3.html) from transcribed audio using the [International Phonetic Alphabet](https://en.wikipedia.org/wiki/International_Phonetic_Alphabet) for word pronunciations. Unknown words have pronunciations predicted with [phonetisaurus](https://github.com/AdolfVonKleist/Phonetisaurus).

This project is inspired by [Zamia Speech](https://github.com/gooofy/zamia-speech), and is intended to supply acoustic models built from [open speech corpora](https://github.com/JRMeyer/open-speech-corpora) to the [Rhasspy project](https://github.com/rhasspy/rhasspy) for [many human languages](https://github.com/synesthesiam/voice2json-profiles).

Check out the [pre-trained models](#pre-trained-models).

## Dependencies

* Python 3.7 or higher
* [CUDA](https://developer.nvidia.com/cuda-zone) and [cuDNN](https://developer.nvidia.com/cudnn)
    * See [installing CUDA](#installing-cuda)
* [Kaldi](https://kaldi-asr.org) compiled with support for CUDA
    * Install CUDA/cuDNN **before** compiling Kaldi
    * See [installing Kaldi](#installing-cuda)
    * Tested on Ubuntu 18.04 (bionic) with CUDA 10.2 and cuDNN 7.6
* [gruut](https://github.com/rhasspy/gruut)
    * Used to generate [IPA](https://en.wikipedia.org/wiki/International_Phonetic_Alphabet) word pronunciations
    
## Data Sources

ipa2kaldi does not automatically download or unpack audio datasets for you. A dataset is expected to exist in a single directory with:

* A `metadata.csv` file
    * Delimiter is `|` and there is no header
    * Either `id|text` (need `--speaker` argument) or `id|speaker|text`
    * Corresponding WAV file must be named `<id>.wav`
* WAV files in 16Khz 16-bit mono PCM format
    
## Installation

Download the source code and create the Python virtual environment:

```sh
$ pip install ipa2kaldi
```

for Raspberry Pi (ARM), you will first need to [manually install phonetisaurus](https://github.com/rhasspy/phonetisaurus-pypi/releases).

## Usage

```sh
$ python3 -m ipa2kaldi /path/to/kaldi/egs/<model_name>/s5 \
    --language <language-code> \
    --dataset /path/to/dataset1 \
    --dataset /path/to/dataset2 \
```

where:

* `<model_name>` is a name you choose
* `<language_code>` is a supported language from [gruut](https://github.com/rhasspy/gruut) like `en-us`

If all goes well, you should now have a Kaldi recipe directory under `egs/<model_name>/s5`.

**Before training**, you must place a gzipped ARPA language model at `egs/<model_name>/s5/lm/lm.arpa.gz`

After that, run:

```sh
$ cd /path/to/kaldi/egs/<model_name>/s5
$ ./run.sh
```

This will train a new TDNN nnet3 model in the recipe directory. It can take a day or two, depending on how powerful your computer is. If a particular training stage fails (see `run.sh`), you can resume with `./run.sh --stage N` where `N` is the stage to start at.

## Training Workflow

The typical training workflow is described below.

1. Training transcriptions are tokenized and cleaned using [gruut](https://github.com/rhasspy/gruut)
2. Vocabulary words looked up in IPA lexicon(s)
    * Unknown words have pronunciations guessed with phonetisaurus model trained on IPA lexicon(s)
3. Lexicon is created from generated/pre-built pronunciations
    * Use `<unk>` for unknown word
    * Use SPN (spoken noise) silence phoneme for `<unk>`
4. Kaldi recipe files are generated
    * Non-silence phones are manually grouped for `extra_questions.txt`
    * SIL, SPN, NSN silence phones
    * SIL is optional
5. Kaldi test/train files are generated
    * 10%/90% data split
    * wav.scp, text, and utt2spk
6. Do Kaldi training with `run.sh` script
    1. Prepares dict/lang directories
    2. Adapts language model for Kaldi
    3. Creates MFCC features
    4. Trains monophone system
    5. Trains triphone system (1b)
    6. Trains triphone system (2b)
    7. Generates iVectors
    8. Generates topology
    9. Gets alignment lattices
    10. Builds tree
    11. Trains [TDNN 250 nnet3 model](https://github.com/gooofy/zamia-speech/#asr-models)

## Recipe Layout

The output of this project is a Kaldi recipe that lives inside your Kaldi `egs` directory, such as `/path/to/kaldi/egs/rhasspy_nnet3_en-us/s5`. When `scripts/doit.sh` succeeds, this directory should contain the following files:

* s5/
  * run.sh
  * export.sh
  * data/
    * conf/
      * mfcc.conf
      * mfcc_hires.conf
      * online_cmvn.conf
    * local/
      * dict/
        * lexicon.txt.gz
          * WORD P1 P2 ...
        * nonsilence_phones.txt
          * Actual phonemes
        * silence_phones.txt
          * SIL
          * SPN
          * NSN
        * optional_silence.txt
          * SIL
        * extra_questions.txt
          * Phones grouped by accents/elongation
    * train/
      * wav.scp
        * UTT_ID /path/to/wav
        * Sorted by UTT_ID
      * utt2spk
        * UTT_ID speaker
        * Sorted by UTT_ID, then speaker
      * text
        * UTT_ID transcription
    * test/
      * wav.scp
        * Same as train
      * utt2spk
        * Same as train
      * text
        * Same as train
  * lm/
    * lm.arpa.gz
      * ARPA language model

## Installing CUDA

Below are summarized instructions from [this Medium article](https://medium.com/@exesse/cuda-10-1-installation-on-ubuntu-18-04-lts-d04f89287130) for Ubuntu 18.04 (bionic) with CUDA 10.2 and cuDNN 7.6.

First, add the CUDA repos:

```sh
$ sudo apt update
$ sudo add-apt-repository ppa:graphics-drivers
$ sudo apt-key adv --fetch-keys  'http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/7fa2af80.pub'
$ sudo bash -c 'echo "deb http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/ /" > /etc/apt/sources.list.d/cuda.list'
$ sudo bash -c 'echo "deb http://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/ /" > /etc/apt/sources.list.d/cuda_learn.list'
```

Next, install CUDA and cuDNN:

```sh
$ sudo apt update
$ sudo apt install cuda-10-2
$ sudo apt install libcudnn7
```

If installation succeeds, add the following text to `~/.profile`

```sh
# set PATH for cuda 10.2 installation in ~/.profile
if [ -d "/usr/local/cuda-10.2/bin/" ]; then
  export PATH=/usr/local/cuda-10.2/bin${PATH:+:${PATH}}
  export LD_LIBRARY_PATH=/usr/local/cuda-10.2/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
fi
```

After rebooting, check if everything works by running `nvidia-smi` and verifying the version of CUDA reported.

## Installing Kaldi

Install dependencies:

```sh
$ sudo apt-get update
$ sudo apt-get install \
    build-essential \
    wget curl ca-certificates \
    libatlas-base-dev libatlas3-base gfortran \
    automake autoconf unzip sox libtool subversion \
    python3 python \
    git zlib1g-dev patchelf rsync
```

Download the Kaldi source code:

```sh
$ git clone git clone https://github.com/kaldi-asr/kaldi.git
```

Build dependencies (replace `-j8` with `-j4` if you have fewer CPU cores):

```sh
$ cd kaldi/tools
$ make -j8
```

Build Kaldi itself (replace `-j8` with `-j4` if you have fewer CPU cores):

```sh
$ cd ../src
$ ./configure --use-cuda --shared --mathlib=ATLAS
$ make depend -j8
$ make -j8
```

See the [getting started guide](https://kaldi-asr.org/doc/tutorial_setup.html) if you have problems.

## Pre-Trained Models

The following `nnet3` models have been trained with `ipa2kaldi` using public speech data:

* Czech
   * [cz_kaldi-rhasspy](https://github.com/rhasspy/cz_kaldi-rhasspy)
* French
   * [fr_kaldi-rhasspy](https://github.com/rhasspy/fr_kaldi-rhasspy)
* German
   * [de_kaldi-rhasspy](https://github.com/rhasspy/de_kaldi-rhasspy)
* Italian
   * [it_kaldi-rhasspy](https://github.com/rhasspy/it_kaldi-rhasspy)
* Spanish
   * [es_kaldi-rhasspy](https://github.com/rhasspy/es_kaldi-rhasspy)
