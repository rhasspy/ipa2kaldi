# "queue.pl" uses qsub.  The options to it are
# options to qsub.  If you have GridEngine installed,
# change this to a queue you have access to.
# Otherwise, use "run.pl", which will run jobs locally
# (make sure your --num-jobs options are no more than
# the number of cpus on your machine.


#activate this if you want to run the corpus with gridengine (http://gridengine.org/)
#export train_cmd="queue.pl -l 'arch=*64*'"
#export decode_cmd="queue.pl -l 'arch=*64*'"
#export cuda_cmd="queue.pl -l gpu=1"

export train_cmd="utils/run.pl"
export decode_cmd="utils/run.pl"
export cuda_cmd="utils/run.pl -l gpu=1"

export nJobs=12
export nDecodeJobs=12
