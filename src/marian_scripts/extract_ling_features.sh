#!/bin/bash
set -eu -o pipefail

# Script that extracts linguistic features
# Arguments:
#		$1 : File that will be parsed (NEEDS TO BE FULL PATH)

# First check if $1 is a full path
if [[ ! "$1" = /* ]]; then
	echo "First argument should be full path"
	exit -1
fi

# Always load default settings from config file here
source config/marian/default_config.sh

# There are a number of paths you need to set yourself in config/marian_default_config.sh
# This scripts needs to know where these folders/scripts are located on your system
# You can also overwrite them here if you want like this:
# CORENLP=""
# TNT=""
# etc

# Function that take as input stanford tagged conll file ($1), number of column to cut ($2) and output-file ($3)
function get_output() {
	cat $1 | cut -d$'\t' -f$2 | sed -e 's/^$/XXXXXX/' | tr '\n' ' ' | sed -e $'s/XXXXXX/\\\n/g' | awk '{$1=$1};1' | sed -e :a -e '/^\n*$/{$d;N;};/\n$/ba' > $3
}

# Better variable name
sent_file=$1
sent_fol=$(dirname "$sent_file")

# First use the stanford CoreNLP parser to get the features
# My results were with the version from 2018-02-27, but perhaps newer versions will give better results
cd $CORENLP
java -cp "*" -Xmx6g edu.stanford.nlp.pipeline.StanfordCoreNLP -annotators tokenize,ssplit,pos,lemma,parse -ssplit.eolonly -file $sent_file -outputDirectory $sent_fol -outputFormat conll

# Save the output of the CONLL type file to individual files for tok, lem, pos, dep
get_output ${sent_file}.conll "2" ${sent_file}.tok
get_output ${sent_file}.conll "3" ${sent_file}.lem
get_output ${sent_file}.conll "4" ${sent_file}.pos
get_output ${sent_file}.conll "7" ${sent_file}.dep
cd -

# Now we will do the CCG tagging - start with the tokenized file
# We have to do some preprocessing of the sentence to prevent easily avoidable errors
# The parser has trouble with sentences including '...', so replace them first by a single dot
# The parser does not process sentences starting with '#', so just remove the hashtag in that case
# Also remove merge multiple spaces into single space
# Also remove things at end of sentence: parser cannot handle '--' or ':' at the end
# Them remove trailing whitespace
# Then add a . if the sentence does not end with either ? ! or .
# Then capitalize the first letter of each line
sed 's/\.\.\./\./g' ${sent_file}.tok | \
sed -e 's/  */ /g' | \
sed -e '/^#/ s/.//' | \
sed -e '/^-/ s/.//' | \
sed -e 's/--[ ]*$/./' | \
sed -e 's/:[ ]*$/./' | \
sed -e 's/[ \t]*$//' | \
sed -e 's/\([^\.\?\!]\)$/\1 ./' | \
sed -e 's/./\u&/' | \
java -Xmx128g -jar ${EASYCCG}easyccg.jar --model $CCG_MODEL --rootCategories S[dcl] S[wq] S[q] NP S[b]\\\\NP S[intj] --outputFormat boxer -l $MAX_SEN_LEN > ${sent_file}.parse.full

# Clean up the parse to semantic parsing input representation
python $PROCESS_PARSE --input_file ${sent_file}.parse.full $DO_TOK > ${sent_file}.ccg

# Finally do semantic tagging
# For more information on semantic tagging check out this paper: https://www.aclweb.org/anthology/W17-6901/
# TnT can only be obtained by contacting Thorsten Brants and filling out the license:
# http://www.coli.uni-saarland.de/~thorsten/tnt/
# If $TNT is not set, we assume you don't want semtagging and skip
if [[ -n "$TNT" ]]; then
	python $SEM_TAGGER --input_file ${sent_file}.tok --tnt $TNT --model $TNT_MODEL > ${sent_file}.sem
fi

