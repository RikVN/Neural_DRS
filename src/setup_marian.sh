#!/bin/bash
set -eu -o pipefail

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


# Download Marian models and put them in a folder
mkdir -p models/marian/
curl -o models/marian/best_gold_only.npz www.let.rug.nl/rikvannoord/DRS/IWCS/models/best_gold_only/model1.npz
curl -o models/marian/best_gold_silver.npz www.let.rug.nl/rikvannoord/DRS/IWCS/models/best_gold_silver/model1.npz
curl -o models/marian/baseline_gold_silver.npz www.let.rug.nl/rikvannoord/DRS/IWCS/models/baseline_gold_silver/model1.npz
