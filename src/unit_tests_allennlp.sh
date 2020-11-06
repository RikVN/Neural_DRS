#!/bin/bash
set -eu -o pipefail

# Give some general information
echo "Test if preprocessing and training AllenNLP models works as expected"
echo "The training/testing of the models can take quite some time and needs to run on GPU"
echo "Expect this script to run well over an hour"; sleep 5
echo
echo "Note: we expect that you followed the setup instructions in the general README"
echo "In other words, the data/ and DRS_parsing/ folders exist and have the correct content"
echo ; sleep 5


##### Preprocessing ######

# First test the preprocessing calls in the README
echo "First do all the English preprocessing as specified in AllenNLP.md" ;sleep 3

for type in train dev test; do
	python src/preprocess.py --input_file DRS_parsing/data/pmb-3.0.0/gold/${type}.txt -v rel -r word -cd .tgt --drss_only
done

for type in train dev test; do
	python src/preprocess.py --sentence_file DRS_parsing/data/pmb-3.0.0/gold/dev.txt.raw -r char -cs .char.sent --sents_only -c feature
done

for type in train dev test; do
	while IFS= read -r line1 && IFS= read -r line2 <&3; do
		echo -e "${line1}\t${line2}"
	done < DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.raw.tok  3< DRS_parsing/data/pmb-3.0.0/gold/${type}.txt.tgt > DRS_parsing/data/pmb-3.0.0/gold/${type}.alp
done

# Now do the German preprocessing
echo "Now do all the non-English preprocessing as specified in AllenNLP.md"; sleep 3
for type in train dev test; do
	python src/preprocess.py --input_file data/3.0.0/de/gold/${type}.txt -v rel -r word -cd .tgt --drss_only
done

for type in train dev test; do
	python src/preprocess.py --input_file data/3.0.0/de/gold/${type}.txt  --sentence_file data/3.0.0/de/gold/${type}.txt.raw -r char -cs .char.sent -cd .char.tgt -v rel -c feature
done

for type in train dev test; do
	while IFS= read -r line1 && IFS= read -r line2 <&3; do
		echo -e "${line1}\t${line2}"
	done < data/3.0.0/de/gold/${type}.txt.raw  3< data/3.0.0/de/gold/${type}.txt.tgt > data/3.0.0/de/gold/${type}.alp
done

for type in train dev test; do
	while IFS= read -r line1 && IFS= read -r line2 <&3; do
		echo -e "${line1}\t${line2}"
	done < data/3.0.0/de/gold/${type}.txt.raw.char.sent  3< data/3.0.0/de/gold/${type}.txt.char.tgt > data/3.0.0/de/gold/${type}.char.alp
done

# Download and unzip PMB GloVe embeddings if the file does not exist yet
if [[ -f "emb/glove.840B.300d.pmb.txt" ]]; then
	echo "Glove embeddings already downloaded, skip"
else
	echo "Downloading and unpacking PMB GloVe embeddings, see emb/"
	mkdir -p emb; cd emb
	wget "http://www.let.rug.nl/rikvannoord/embeddings/glove_pmb.zip"
	unzip glove_pmb.zip; rm glove_pmb.zip;  cd ../
fi

##### EXPERIMENTS ######

echo "Now do experiments for English/German, mostly with BERT models" ; sleep 5

# Script that tests our setup for AllenNLP: test small models of our most important model settings
PIPELINE="src/allennlp_scripts/pipeline.sh"
CONFIG="config/allennlp/en/"
EXPS="experiments/allennlp/en/"

mkdir -p $EXPS

# Remove all current models in exps to have a fresh new test
rm -r $EXPS/* || true

# Experiments are in order of likelihood to fail

# Sem + char in 2 encoders
$PIPELINE ${CONFIG}/bert_char_sem.json ${EXPS}/bert_char_sem/ normal en

# Sem + char in 2 encoders - fine-tuning
$PIPELINE ${CONFIG}/bert_char_sem_fine.json ${EXPS}/bert_char_sem/ fine en

# Bert + char in two encoders
$PIPELINE ${CONFIG}/bert_char_2enc.json ${EXPS}/bert_char_2enc/ normal en

# BERT + char in 1 encoder
$PIPELINE ${CONFIG}/bert_char_1enc.json ${EXPS}/bert_char_1enc/ normal en

# Test BERT model
$PIPELINE ${CONFIG}/bert.json ${EXPS}/bert/ normal en

#### Now run the experiments for German

DE_EXPS="experiments/allennlp/de/"
DE_CONFIG="config/allennlp/de/"

mkdir -p $DE_EXPS
rm -r $DE_EXPS/* || true

# Just characters (note that this has the wrong settings in settings.sh
# see AllenNLP.md, but we run it here just to test if it works without errors

$PIPELINE ${DE_CONFIG}/char.json ${DE_EXPS}/char/ normal de

# Bert + char in two encoders
$PIPELINE ${DE_CONFIG}/bert_char_2enc.json ${DE_EXPS}/bert_char_2enc/ normal de

# BERT + char in 1 encoder
$PIPELINE ${DE_CONFIG}/bert_char_1enc.json ${DE_EXPS}/bert_char_1enc/ normal de

# Test BERT model
$PIPELINE ${DE_CONFIG}/bert.json ${DE_EXPS}/bert/ normal de

echo
echo "If you see this, the experiments did not throw any errors"
