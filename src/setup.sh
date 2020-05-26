#!/bin/bash
set -eu -o pipefail

# Get OpenNMT, and use the version to reproduce experiments with
# Newer versions might work as well, not tested
# All experiments are with the Torch version, which is no longer maintained
# Though for reproducibility I still use it for these scripts
git clone https://github.com/OpenNMT/OpenNMT/
cd OpenNMT
git checkout 2d9bc10
cd ../

# Get the DRS parsing repo with the scripts (Counter) and data
git clone https://github.com/RikVN/DRS_parsing
cd DRS_parsing

pip install -r requirements.txt
pip install scipy
cd ../

# Get the 3.0.0 data
#wget "https://pmb.let.rug.nl/releases/pmb_exp_data_3.0.0.zip"
# PMB website is down, temporarily get the files from here
wget "http://www.let.rug.nl/rikvannoord/pmb_release/pmb_exp_data_3.0.0.zip"
unzip pmb_exp_data_3.0.0.zip

# The files in the DRS_parsing repo only have gold and silver separately
# Combine them to files with gold + silver to reproduce experiments
# You can use similar scripts to do gold + bronze, gold + silver + bronze, etc
for fol in DRS_parsing/data/pmb-2.1.0 DRS_parsing/data/pmb-2.2.0 pmb_exp_data_3.0.0/en/ ; do
	cd $fol
	mkdir -p gold_plus_silver
	cat gold/train.txt silver/train.txt > gold_plus_silver/train.txt
	cat gold/train.txt.raw silver/train.txt.raw > gold_plus_silver/train.txt.raw
	# Also put the dev files there, but they are just gold
	cp gold/dev.txt gold_plus_silver/dev.txt
	cp gold/dev.txt.raw gold_plus_silver/dev.txt.raw
	cd -
done


# Download easyccg and model (use PMB forked version)
git clone https://github.com/ParallelMeaningBank/easyccg
cd easyccg
ant
wget "http://www.let.rug.nl/rikvannoord/easyCCG/model.tar.gz"
tar xvzf model.tar.gz
cd -

# Download and set up stanford CoreNLP
# Instructions from: https://stanfordnlp.github.io/CoreNLP/download.html
# Check if you have the correct java version installed
# java -version should complete successfully with a line like: java version "1.8.0_92".
wget http://nlp.stanford.edu/software/stanford-corenlp-full-2018-10-05.zip
unzip stanford-corenlp-full-2018-10-05.zip

# Install Marian: https://marian-nmt.github.io/docs/
# Same as for OpenNMT: there are newer versions available, but for
# reproducibility we revert back to a previous version
# But could very well be that there are no practical differences
git clone https://github.com/marian-nmt/marian
cd marian
git checkout b2a945c
# Build
mkdir build
cd build
cmake ..
make -j
cd ../../
printf "Please check: https://marian-nmt.github.io/docs/ if you have all dependencies needed to run Marian\n\n"
sleep 5 # time to read the message

# Download pretrained OpenNMT/Marian models and put them in a folder
mkdir -p models/opennmt/
mkdir -p models/marian/
# Marian
curl -o models/marian/best_gold_only.npz www.let.rug.nl/rikvannoord/DRS/IWCS/models/best_gold_only/model1.npz
curl -o models/marian/best_gold_silver.npz www.let.rug.nl/rikvannoord/DRS/IWCS/models/best_gold_silver/model1.npz
curl -o models/marian/baseline_gold_silver.npz www.let.rug.nl/rikvannoord/DRS/IWCS/models/baseline_gold_silver/model1.npz
# OpenNMT
curl -o models/opennmt/best_gold_only.npz www.let.rug.nl/rikvannoord/DRS/TACL/models/best_gold_only/gpu/model_run1.t7
curl -o models/opennmt/best_gold_silver.npz www.let.rug.nl/rikvannoord/DRS/TACL/models/best_model/gpu/model_run1.t7
