# Marian

Here, we describe how to reproduce our results from our [IWCS paper](https://www.aclweb.org/anthology/W19-0504/) using [Marian](https://marian-nmt.github.io/).

Make sure you ran ``src/setup.sh`` and followed the instructions in the README. Next, we will install the necessary software. I advise creating a Conda environment to install the dependencies. My own Python scripts are for Python 3.

You can run this command to install my version of Marian:

```
./src/setup_marian.sh
```

There are a few things that this script does not take care of, but need to be installed: [Apache Ant](https://ant.apache.org/) (for easyCCG), [cmake](https://cmake.org/install/) (for building Marian) and You will have to install software to get the linguistic features ([CoreNLP](https://stanfordnlp.github.io/CoreNLP/download.html) and [easyCCG](https://github.com/ParallelMeaningBank/easyccg)) for the linguistic features.

Note: if you want to run Marian on CPU, check out [this fork](https://github.com/dhgoratela/Neural_DRS) by [dhgoratela](https://github.com/dhgoratela) and especially [this script](https://github.com/dhgoratela/Neural_DRS/blob/v2.2.0-marian-cpu/src/marian_cpu_preset.sh).

## Configuration ##

In config/marian/default_config.sh we store the default settings for preprocessing, training and parsing. All shell scripts read from there. It should work if you use our setup, but if you encounter any weird errors please check if the filepaths are set correctly for you.

If you do not have access to GPU, you'll have to change the gpuid setting as well.

## Testing your setup ##

If you want to check that everything is installed/downloaded/setup correctly, simply run this:

```
./src/unit_tests_marian.sh
```

This does a range of tests and can only succeed if everything works. Note that this requires to be run on GPU!

## Running experiments ##

Here we will outline how you can run new experiments and parse sentences with our best model.

### Linguistic features ###

The models trained with Marian can use linguistic features (but don't have to necessarily). We use [CoreNLP](https://stanfordnlp.github.io/CoreNLP/download.html), [easyCCG](https://github.com/ParallelMeaningBank/easyccg) and the TNT tagger (Semantic tags) to obtain the features. Running ``setup.sh`` should take care of the first two, but for TNT you need to fill in [a license](http://www.coli.uni-saarland.de/~thorsten/tnt/) to get the system (sorry). Our best model only uses lemmas, though, so having the tagger is only necessary to reproduce my gold-only results. Also, you could potentially replace it with your own tagger.

You can extract all the linguistic features (lem/pos/dep/sem/ccg) using ``src/marian_scripts/extract_ling_features.sh``, like this:

```
./src/marian_scripts/extract_ling_features.sh $SENT_FILE
```

$SENT_FILE should not be tokenized already, we use CoreNLP to do that. If $TNT is not set in the default config, it simply skips semtagging.

As we do in the paper, it is possible to combine features in a single input file. You can merge them like this:

```
python src/merge_tags.py -f ${SENT_FILE}.feat.pos ${SENT_FILE}.feat.dep ${SENT_FILE}.feat.ccg ${SENT_FILE}.feat.lem --char_exts .feat.lem > ${SENT_FILE}.multi
```

By using --char_exts you specify which files (by extension) should be in character-level representation. In our setup, this only makes sense for the lemmas.

**Note**: if you don't want to bother with linguistic features, you can use our baseline gold + silver model for the parsing (baseline_gold_silver.sh), which is only slightly worse than using the features.

### Parsing from raw text ###

If you're only interested in parsing from raw text, please download one of our [pretrained models](http://www.let.rug.nl/rikvannoord/DRS/IWCS/models/). Probably you want to use our best model, which is gold + silver with lemmas as extra linguistic features (best_gold_silver). Note that ``setup_marian.sh`` should have already handled this (check models/).

First extract the linguistic features for you sentence file as described above, using ``extract_ling_features.sh``.

Then, for our best silver model, you have to preprocess the lemma features to a char-level representation.

```
python src/merge_tags.py -f ${SENT_FILE}.feat.lem --char_exts .feat.lem > ${SENT_FILE}.clem
```

The parse script will automatically take care of preprocessing the raw sentence file, using the settings as described in the specific config file.

Now to the actual parsing. You have to use the config file that fits with the model you chose, i.e. use config/marian/best_gold_silver.sh if you use our best silver model. Obviously, fill in the variables yourself, depending on where you put the file(s):

```
./src/marian_scripts/parse_raw_text.sh config/marian/best_gold_silver.sh $PRETRAINED_MODEL $OUTPUT_FILE $SENT_FILE ${SENT_FILE}.clem
```

This will automatically postprocess your file to ${OUTPUT_FILE}.res. Also, ${OUTPUT_FILE}.res.log will contain information about this process.

### Training your own model ###

The script ``src/marian_scripts/pipeline.sh`` can be used to run your own experiments. Again, note that each experiment needs its own config file. I have added examples of config files in config/marian/, which can also be used to train our best gold-only and best general model.

**Make sure that the models have access to the files with linguistic features**, as is described above. In config/marian/default_config.sh you can see which settings can be overwritten to create different experiments.

If you want to use the gold_silver data, the model expects the dev set to be in the same folder as train, so we copy it there:

```
cp data/3.0.0/en/gold/dev.txt data/3.0.0/en/gold_silver/
cp data/3.0.0/en/gold/dev.txt.raw data/3.0.0/en/gold_silver/
```

Some things to note: if $PRETRAINED_FOLDER and $FINETUNED_FOLDER are both set, it automatically does pretraining + finetuning. If you only want "normal" training, leave $FINETUNED_FOLDER empty. Our best silver model can simply be reproduced by this:

```
./src/marian_scripts/pipeline.sh config/marian/best_gold_silver.sh
```
