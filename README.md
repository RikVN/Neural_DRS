# Neural DRS parsing

This folder contains scripts to use our neural seq2seq model to produce DRSs. It contains code to reproduce either our [TACL paper](https://www.aclweb.org/anthology/Q18-1043.pdf), our [IWCS paper](https://www.aclweb.org/anthology/W19-0504/) or our [EMNLP paper](https://www.aclweb.org/anthology/2020.emnlp-main.371.pdf). The models rely on [OpenNMT](http://opennmt.net/), [Marian](https://marian-nmt.github.io/) and [AllenNLP](https://allennlp.org/), respectively.

Information about reproducing the specific papers are in separate READMEs. This README helps in setting up all DRS parsing experiments.

## Getting Started

```
git clone https://github.com/RikVN/Neural_DRS
cd Neural_DRS
```

This repository works with PMB release 3.0.0. If you want to work with 2.2.0 (or older), run this:

```
git checkout v2.2.0-final
```

### Setup & Data

First we will setup the datasets and the [DRS_parsing respository](https://github.com/RikVN/DRS_parsing), which is needed for evaluation.

Make sure DRS_parsing/ and DRS_parsing/evaluation/ are on your $PYTHONPATH (though they are yet to be created), e.g. like this:

```
cur_dir=$(pwd)
export PYTHONPATH=${cur_dir}/DRS_parsing/:${PYTHONPATH}
export PYTHONPATH=${cur_dir}/DRS_parsing/evaluation/:${PYTHONPATH}
```

I strongly advise to create a conda environment for this repository:

```
conda create -n ndrs python=3.6
conda activate ndrs
```

I made a script ``setup.sh`` that takes care of setting everything up. Throughout the README I assume you ran this.

```
./src/setup.sh
```

**Important:** all data you need for running basic DRS parsing experiments you can now find in data/. You can potentially still download a [PMB release](http://pmb.let.rug.nl/data.php) and construct the training data yourself, but I'd advise not to unless you want to exploit more resources.

### Testing your setup ###

We want to be sure that all scripts that are independent of your (neural) parsing software work. This includes preprocessing, postprocessing, Counter, Referee and DRS jury. This command should succeed without errors:

```
./src/unit_tests.sh
```

## Running experiments ##

For each of the three Neural DRS parsing papers, I have written separate READMEs. They explain how to reproduce our work, use our best parser and run your own experiments. Please find the links below:

* [TACL paper with OpenNMT](OpenNMT.md)
* [IWCS paper with Marian](Marian.md)
* [EMNLP paper with AllenNLP](AllenNLP.md)

## DRS Jury ##

I created a script to give a better overview of your DRS parsing system, called [DRS Jury](DRS_jury.md). It has the same capabilities as Counter, and includes the following extensions:

* Averaging over multiple output files (recommended)
* Comparing different experiments across a number of scores
* Individual scores per clause type (e.g. F-score on just predicting "Agent")
* Analysis of performance on infrequent word senses
* F-score over sentence-length plots
* Statistical tests between two experiments
* Semantic tag analysis (e.g. how well do we score on negation)
* Listing the hardest documents per experiment
* Listing the relatively easiest/hardest documents compared to the other experiment
* Individual analysis of these documents, with example output per document

Details on how to run are specified in this [README](DRS_jury.md). Example run command:

```
python src/drs_jury.py --folders output/pmb-3.0.0/en/dev/bert_only/ output/pmb-3.0.0/en/dev/bert_char_1enc/ --prefix output -de .txt --working tst/unit/ --names bert_only bert_char_1enc
```

## Semtag analysis ##

In our most recent [paper](https://www.aclweb.org/anthology/2020.emnlp-main.371.pdf) we introduced the idea of analysis by [semtags](https://www.aclweb.org/anthology/W17-6901.pdf). The evaluation tool semtag_analysis.py gives a score for a number of semantic/linguistic phenomena, which are selected based on which semtags the sentence contains. An example score on PMB 3.0.0 dev looks like this:

<pre>
Exp            	Docs 	bert_only 	bert_char_1enc 
All            	885  	0.876     	0.881          
Modal          	100  	0.869     	0.868          
  Negation     	77   	0.895     	0.895          
  Possibility  	23   	0.784     	0.790          
  Necessity    	9    	0.788     	0.783          
Logic          	209  	0.856     	0.863          
Pronouns       	497  	0.882     	0.885          
Attributes     	513  	0.873     	0.879          
Comparatives   	21   	0.785     	0.825          
Named Entities 	320  	0.875     	0.878          
Numerals       	66   	0.822     	0.838 
</pre>

This works for DRS parsing, but is potentially applicable to all NLP tasks that have a sentence as input, with a single score per sentence. For a more detailed explanation of the process and instructions on how to setup and run, see this [README](Semtags.md).

## Scores & Output ##

If you're only interested in the output of our parser(s), please check the [output](output) folder.  We have added parser output for release 2.1.0, 2.2.0 and 3.0.0. 

The [specific scores](Scores.md) are also available. If you want to add your scores to the table, consider doing a pull request.

## Citation ##

This repository contains code and documentation for three semantic parsing papers.

For OpenNMT and Referee, please cite:

* Rik van Noord, Lasha Abzianidze, Antonio Toral and Johan Bos. **Exploring Neural Methods for Parsing Discourse Representation Structures.** TACL 2018 [\[PDF\]](https://www.aclweb.org/anthology/Q18-1043.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/Q18-1043.bib)

For Marian and linguistic feature extraction, please cite:

* Rik van Noord, Antonio Toral and Johan Bos. **Linguistic Information in Neural Semantic Parsing with Multiple Encoders.** IWCS 2019 [\[PDF\]](https://www.aclweb.org/anthology/W19-0504.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/W19-0504.bib)

For AllenNLP (BERT), Semantic tag analysis and DRS Jury, please cite:

* Rik van Noord, Antonio Toral and Johan Bos. (2020) **Character-level Representations Improve DRS-based Semantic Parsing Even in the Age of BERT.** EMNLP 2020 [\[PDF\]](https://www.aclweb.org/anthology/2020.emnlp-main.371.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/2020.emnlp-main.371.bib)

If you use Counter, please cite:

* Rik van Noord, Lasha Abzianidze, Hessel Haagsma, and Johan Bos. **Evaluating scoped meaning representations**. LREC 2018 [\[PDF\]](https://www.aclweb.org/anthology/L18-1267.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/L18-1267.bib)

If you use data from the PMB, please cite:

* Abzianidze, L., Bjerva, J., Evang, K., Haagsma, H., van Noord, R., Ludmann, P., Nguyen, D. & Bos, J. **The Parallel Meaning Bank: Towards a Multilingual Corpus of Translations Annotated with Compositional Meaning Representations**, EACL 2017 [\[PDF\]](https://www.aclweb.org/anthology/E17-2039.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/E17-2039.bib)

We also keep a list of all papers related to DRS parsing [here](https://pmb.let.rug.nl/publications.php). Let us know if you want your paper included.

## Author

* **Rik van Noord** - PhD-student at University of Groningen - [Personal website](http://www.rikvannoord.nl)

## Acknowledgments

* Thanks to my co-authors Antonio, Hessel, Johan and Lasha, and all members of the [Parallel Meaning Bank](http://pmb.let.rug.nl)
