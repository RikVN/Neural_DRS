#!/bin/bash
# Default settings that are imported for each experiment
# Might be overwritten per individual experiment in different config files

## First we list the settings that have to be present in each config file and never here!
## That is the reason they are commented

# MAIN_FOLDER=""
# GOLD_FOLDER=""
# gold_train=""
# gold_dev=""
# var_rewrite=""
# representation=""
# end_epoch=""
# num_runs=1

###### IMPORTANT TO SET THESE ######

# Hacky method to set the folder, you can also comment the three lines below out
# and set the folder like this:
# GIT_HOME="/your/folders/here/Neural_DRS/"
cd ../
GIT_HOME="$(pwd)/"  # where the Git Neural_DRS repository is located
cd OpenNMT

ONMT_HOME="${GIT_HOME}/OpenNMT/"        # where OpenNMT is located
gpuid="-gpuid 1"                        # Use -gpuid 1 if training from GPU, otherwise 0 for cpu
sig_file="${GIT_HOME}DRS_parsing/evaluation/clf_signature.yaml" # signature file for clf_referee, check if correct location

# File from which to train pre-trained embeddings. When recreating our experiments, you can download these embeddings here:
# http://www.let.rug.nl/rikvannoord/DRS/embeddings/
# Not necessary to set this parameter if you only do character-level training
embed_file=""
embed_type="glove"

##### PARAMETER SETTINGS FOR EXPERIMENTS #####

# These are the default settings that will be used if you do not specify them in your own config file
# If you do specify them in your own config file, these values will be overridden

# Parameter settings for preprocessing
src_words_min_frequency="3"
tgt_words_min_frequency="3"
src_seq_length="1000"
tgt_seq_length="1000"

# Parameter settings for training
src_word_vec_size="300"
tgt_word_vec_size="300"
layers="2"
rnn_size="300"
rnn_type="LSTM" #options LSTM (default), GRU
dropout="0.2"
dropout_input=""           #boolean, use as -dropout_input (default false)
dropout_words="0"          #dropout probability applied to the source sequence (default 0)
dropout_type="naive"       #dropout type, options naive (default) or variational
residual=""                #boolean, add residual connections between recurrent layers (default empty is false)
bridge="copy"              #define how to pass encoder states to the decoder. With copy, the encoder and decoder must have the same number of layers. Accepted: copy, dense, dense_nonlinear, none; default: copy
encoder_type="brnn"        #accepted: rnn, brnn, dbrnn, pdbrnn, gnmt, cnn; default: rnn
attention="global"         #none or global (default)
max_pos="1000"             #maximum value for positional indexes (default 50)
global_attention="general" #accepted: general, dot, concat; default: general

#Trainer/optimizer options
report_every="100"             #default 50
validation_metric="perplexity" #accepted: perplexity, loss, bleu, ter, dlratio; default: perplexity
max_batch_size="12"            #default 64
optim="sgd"                    #optimizer, accepted: sgd, adagrad, adadelta, adam
learning_rate="0.7"            #Initial learning rate. If adagrad or adam is used, then this is the global learning rate. Recommended settings are: sgd = 1, adagrad = 0.1, adam = 0.0002.
max_grad_norm="5"              #Default 5. Clip the gradients L2-norm to this value. Set to 0 to disable.
learning_rate_decay="0.7"      #Default 0.7
start_decay_at="9"             #In "default" decay mode, start decay after this epoch.
train_from=""                  #Add this if we want to train from a checkpoint (use -train_from FOLDER and -continue as well)

# Parameter settings for testing
batch_size_test="12"        #batch size test
beam_size="10"
max_sent_length="1000"      #default 250
replace_unk="-replace_unk"  #boolean, default empty
n_best="1"                  #If > 1, it will also output an n-best list of decoded sentences.
length_norm="0.90"
coverage_norm="0"           #Coverage normalization coefficient (beta). An extra coverage term multiplied by beta is added to hypotheses scores. If is set to 0 (default), no coverage normalization.
eos_norm="0"                #End of sentence normalization coefficient (gamma). If set to 0 (default 0), no EOS normalization.
log_level="WARNING"         #accepted: DEBUG, INFO, WARNING, ERROR, NONE; default: INFO

# Create script names already here

SRCPATH="${GIT_HOME}src/"

ens_py="ensemble_best_models.py"
cv_py="create_cv_files.py"
stat_py="create_stat_files.py"
avg_exp_score="avg_exp_score.py"

PREPROCESS_PYTHON="${SRCPATH}preprocess.py"
PREPROCESS_LUA="${ONMT_HOME}preprocess.lua"
PREPROCESS_SH="${SRCPATH}/opennmt_scripts/preprocess.sh"
EMBED_LUA="${ONMT_HOME}tools/embeddings.lua"
TRAIN_LUA="${ONMT_HOME}train.lua"
TRAIN_SH="${SRCPATH}/opennmt_scripts/train.sh"
PARSE_SH="${SRCPATH}opennmt_scripts/parse.sh"
TRANSLATE_LUA="${ONMT_HOME}translate.lua"
POSTPROCESS_PY="${SRCPATH}postprocess.py"

# Embedding names and files

embed="embeddings/"
src_id="src"
tgt_id="tgt"
emb_ext="-embeddings-300.t7"
pre_word_vecs_enc=""
pre_word_vecs_dec=""

# Extensions of files we will create
char_drs_ext=".char.drs"
char_sent_ext=".char.sent"
sent_ext=".raw"
valid_drs_ext=".valid.drs"
var_drs_ext=".var"
output_ext=".seq.drs"
log_ext=".log"
res_ext=".res"
eval_ext=".txt"
MODEL_EXT="*.t7"
txt_ext=".txt"

# Log file
log_file_train="train.log"

# Names of things we add to file
VOCAB_NAME="vcb"

# Vocab we train from (usually $MAIN_FOLDER$VOCAB$VOCAB_NAME$ext_src except for pretrain experiments)

ext_src=".src.dict"
ext_tgt=".tgt.dict"

# List of folder names

WORKING="working/"
VOCAB="vocab/"
MODELS="models/"
OUTPUT="output/"
EVAL="evaluation/"
LOG="log/"
TRAIN="train/"
DEV="dev/"
TEST="test/"
