# OpenNMT

Here, we describe how to run the OpenNMT system we used in our [TACL paper](https://www.mitpressjournals.org/doi/abs/10.1162/tacl_a_00241).

## Setup

Make sure you ran ``src/setup.sh``.  Next, we will install the necessary software. I advise creating a Conda environment to install the dependencies. My own Python scripts are for Python 3.

You can run this command to install my version of OpenNMT (Torch-based):

```
./src/setup_opennmt.sh
```

You probably need to install some dependencies separately, such as [Torch](http://torch.ch/docs/getting-started.html) and the corresponding packages.

If you want to use an ensemble during parsing for OpenNMT, you will have to checkout the ensemble branch. Instructions on how to do that are [here](http://forum.opennmt.net/t/ensemble-decoding/115/11). Note that you have to specify $ONMT_HOME in config/opennmt/default_config.sh to the correct location of this branch.

## Configuration

In config/opennmt/default_config.sh we store the default settings for preprocessing, training and parsing. All shell scripts read from there. **You will have to set the correct paths yourself.** The scripts need to know where the current repo is located, and perhaps other locations are also different on your machine.

If you do not have access to GPU, you'll have to change the gpuid setting as well (all my experiments are on GPU, not sure if it will work).

### Testing your setup ###

If you want to check that everything is installed/downloaded/setup correctly, simply run this:

```
./src/unit_tests_opennmt.sh
```

This does a range of tests for the OpenNMT and can only succeed if everything works. Note that this requires to be run on GPU!

## Running experiments ##

First I'll describe how to run experiments with OpenNMT, which we described in [this paper](https://www.mitpressjournals.org/doi/abs/10.1162/tacl_a_00241)

## Running from OpenNMT folder ##

**IMPORTANT:** You have to run the training and parsing scripts with the OpenNMT directory as your working folder. We will assume that the OpenNMT folder is located in this Github folder when giving instructions on how to run. If you put the OpenNMT folder somewhere else, you'll have to change where preprocess.sh, train.sh and parse.sh read default_config.sh from!

### Parsing raw text

If you only want to do parsing, please download (one of) our [pre-trained models](http://www.http://www.let.rug.nl/rikvannoord/DRS/TACL/models/). If you ran ``setup_opennmt.sh``, the GPU models should already be downloaded. You can choose between our best gold-only models, or our best model in general, that is also trained on the silver data released in PMB 2.1.0.

When using one of those models, you will have to preprocess the input to the input structure the model expects.

For all the models there, $SENT_FILE should not be tokenized, and then put in char-level format, with a feature indicating casing:

```
python src/preprocess.py -s $SENT_FILE -c feature -r char --sents_only
```

Then do the parsing. If you specify multiple models, it will automatically be an ensemble, **but this might get out of GPU memory for longer, non-PMB input**. The config file to use for both the models is config/opennmt/parse_best_config.sh. Note that this config-file can only be used for parsing, not training. 

Make sure to check default_config.sh and parse_best_config.sh to make sure your local folders are set correctly. Then, run the parser like this:

```
cd OpenNMT
../src/opennmt_scripts/parse.sh ../config/opennmt/parse_best_config.sh $INPUT_FILE $OUTPUT_FILE $MODEL1 [$MODEL2] [$MODEL3] ...
```

The output will be automatically postprocessed to a valid CLF format. Invalid DRSs will be replaced by dummy (but valid) ones.

Note that these models were trained on mainly short sentences (up to 15 tokens). Most likely they won't perform that well for long sentences.

### Training

You already set up config/opennmt/default_config.sh. That contains all our default settings for experiments. However, if you want to run your own experiments you have to set your own parameters. The config folder already contains an example for our baseline model you can finish (config/opennmt/baseline.sh).

Make sure that you specify a folder for the experiment (will be created) where all information (models, input, output, vocab, logs) is saved. Also, specify where the train and dev data is located. **Every experiment needs such a config file!**

The examples here are for sample data, just to show that it works. Start by preprocessing the data:

```
cd OpenNMT
../src/opennmt_scripts/preprocess.sh ../config/opennmt/sample.sh
```

If there are no errors, you can train like this:

```
../src/opennmt_scripts/train.sh ../config/opennmt/sample.sh
```

This will most likely take some time. If training is finished, you can parse new files in the following way:

```
../src/opennmt_scripts/parse.sh ../config/opennmt/sample.sh $INPUT_FILE $OUTPUT_FILE $MODEL1 [$MODEL2] [$MODEL3] ...
```

Noe that the input file should be in the correct character-level format (src/preprocess.py). The output will be automatically postprocessed. You can only use multiple models if you are using the ensemble branch of OpenNMT (see above).

If you parsed a gold standard dev/test set, you can calculate an F-score by using Counter:

```
python ../DRS_parsing/evaluation/counter.py -f1 $CLF_OUTPUT -f2 $GOLD_DEV
```

The baseline model should score somewhere between 74 and 76 in F-score. You can create your own config files to perform different experiments.
