#!/bin/bash

# Folders
NEURAL_GIT=$(pwd)
DRS_GIT="${NEURAL_GIT}/DRS_parsing/"
SRC_PYTHON="${NEURAL_GIT}/src/"

# Files
PP_PY="${SRC_PYTHON}sbn_postprocess.py"

# Setting for postprocessing
MIN_TOKENS=5

# Settings for experiments
SILENT="--silent"   # silent parsing
FORCE="-f"          # force reprocessing if directory already exists

# For tarring our own models
VOCAB="vocabulary/"
CONFIG="config.json"
model_file="model.tar.gz"
