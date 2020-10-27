#!/bin/bash
set -eu -o pipefail

# Setup the OpenNMT Github and download the models

# Get OpenNMT, and use the version to reproduce experiments with
# Newer versions might work as well, not tested
# All experiments are with the Torch version, which is no longer maintained
# Though for reproducibility I still use it for these scripts
git clone https://github.com/OpenNMT/OpenNMT/
cd OpenNMT
git checkout 2d9bc10
cd ../

# Download pretrained OpenNMT models and put them in a folder
mkdir -p models/opennmt/
curl -o models/opennmt/best_gold_only.npz www.let.rug.nl/rikvannoord/DRS/TACL/models/best_gold_only/gpu/model_run1.t7
curl -o models/opennmt/best_gold_silver.npz www.let.rug.nl/rikvannoord/DRS/TACL/models/best_model/gpu/model_run1.t7
