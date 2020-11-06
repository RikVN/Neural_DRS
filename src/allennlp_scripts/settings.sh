#!/bin/bash

# Folders
NEURAL_GIT=$(pwd)
DRS_GIT="${NEURAL_GIT}/DRS_parsing/"
SRC_PYTHON="${NEURAL_GIT}/src/"

# Files
PP_PY="${SRC_PYTHON}postprocess.py"
SIG_FILE="${DRS_GIT}evaluation/clf_signature.yaml"
COUNTER="${DRS_GIT}evaluation/counter.py"

# Setting for postprocessing
REMOVE_CLAUSES=75
SEP="|||"
# Use this for word-based exps
no_sep="--no_sep"
MIN_TOKENS=10

# NOTE:
# Use this for character-level exps
#no_sep=""
#MIN_TOKENS=20

# Settings for experiments
FORCE_PP=true       # whether we force postprocessing or skip if already there
SILENT="--silent"   # silent parsing
FORCE="-f"          # force reprocessing if directory already exists

# For tarring our own models
VOCAB="vocabulary/"
CONFIG="config.json"
model_file="model.tar.gz"
