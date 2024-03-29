#!/usr/bin/env bash
# Copyright Johns Hopkins University (Author: Daniel Povey) 2012.  Apache 2.0.

# This script produces CTM files from a training directory that has alignments
# present.


# begin configuration section.
cmd=run.pl
frame_shift=0.01
stage=0
use_segments=true # if we have a segments file, use it to convert
                  # the segments to be relative to the original files.
print_silence=false # if true, will print <eps> (optional-silence) arcs.

#end configuration section.

echo "$0 $@"  # Print the command line for logging

[ -f ./path.sh ] && . ./path.sh
. parse_options.sh || exit 1;

if [ $# -ne 3 ] && [ $# -ne 4 ]; then
  echo "Usage: $0 [options] <data-dir> <lang-dir> <ali-dir|model-dir> [<output-dir>]"
  echo "(<output-dir> defaults to  <ali-dir|model-dir>.)"
  echo " Options:"
  echo "    --cmd (run.pl|queue.pl...)      # specify how to run the sub-processes."
  echo "    --stage (0|1|2)                 # start scoring script from part-way through."
  echo "    --use-segments (true|false)     # use segments and reco2file_and_channel files "
  echo "                                    # to produce a ctm relative to the original audio"
  echo "                                    # files, with channel information (typically needed"
  echo "                                    # for NIST scoring)."
  echo "    --frame-shift (default=0.01)    # specify this if your alignments have a frame-shift"
  echo "                                    # not equal to 0.01 seconds"
  echo "e.g.:"
  echo "$0 data/train data/lang exp/tri3a_ali"
  echo "Produces ctm in: exp/tri3a_ali/ctm"
  exit 1;
fi

data=$1
lang=$2 # Note: may be graph directory not lang directory, but has the necessary stuff copied.
ali_dir=$3
dir=$4
if [ -z $dir ]; then
  dir=$ali_dir
fi


model=$ali_dir/final.mdl # assume model one level up from decoding dir.


for f in $lang/words.txt $model $ali_dir/ali.1.gz $lang/oov.int; do
  [ ! -f $f ] && echo "$0: expecting file $f to exist" && exit 1;
done

oov=`cat $lang/oov.int` || exit 1;
nj=`cat $ali_dir/num_jobs` || exit 1;
split_data.sh $data $nj || exit 1;
sdata=$data/split$nj

mkdir -p $dir/log || exit 1;

if [ $stage -le 0 ]; then
    $cmd JOB=1:$nj $dir/log/get_phones.JOB.log \
         set -o pipefail '&&' linear-to-nbest "ark:gunzip -c $ali_dir/ali.JOB.gz|" \
         "ark:utils/sym2int.pl --map-oov $oov -f 2- $lang/words.txt < $sdata/JOB/text |" \
         '' '' ark:- \| \
         lattice-align-words $lang/phones/word_boundary.int $model ark:- ark:- \| \
         nbest-to-prons $model ark:- - \| \
         utils/int2sym.pl -f 4 $lang/words.txt \| \
         utils/int2sym.pl -f 5- $lang/phones.txt \| \
         gzip -c '>' $dir/phones.JOB.gz || exit 1
fi

if [ $stage -le 1 ]; then
  for n in `seq $nj`; do gunzip -c $dir/phones.$n.gz; done > $dir/phones || exit 1;
  rm $dir/phones.*.gz
fi
