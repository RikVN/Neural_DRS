# Neural DRS parsing

This folder contains scripts to use our neural seq2seq model to produce DRSs. It contains code to reproduce either our [TACL paper](https://www.aclweb.org/anthology/Q18-1043.pdf), our [IWCS paper](https://www.aclweb.org/anthology/W19-0504/) or our EMNLP paper. The models rely on [OpenNMT](http://opennmt.net/), [Marian](https://marian-nmt.github.io/) and [AllenNLP](https://allennlp.org/), respectively.

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

Make sure DRS_parsing/ and DRS_parsing/evaluation/ are on your $PYTHONPATH, e.g. like this:

```
cur_dir=$(pwd)
export PYTHONPATH=${cur_dir}/DRS_parsing/:${PYTHONPATH}
export PYTHONPATH=${cur_dir}/DRS_parsing/evaluation/:${PYTHONPATH}
```

I made a script ``setup.sh`` that takes care of setting everything up. Throughout the README I assume you ran this.

```
./src/setup.sh
```

All data you need for running basic DRS parsing experiments you can now find in [data](data). You can potentially still download a [PMB release](http://pmb.let.rug.nl/data.php) and construct the training data yourself, but I'd advise not to unless you want to exploit more resources.

### Testing your setup ###

We want to be sure that all scripts that are independent of your (neural) parsing software work. This includes preprocessing, postprocessing, Counter, Referee and DRS jury. This command should succeed without errors:

```
./src/unit_tests.sh
```

## DRS Jury ##

Explanation coming soon, it's available [here](src/drs_jury.py).

## Running experiments ##

For each of the three papers, I have written separate READMEs. Please find the links below:

* [TACL paper with OpenNMT](OpenNMT.md)
* [IWCS paper with Marian](Marian.md)
* EMNLP paper with AllenNLP (coming soon)

## Scores & Output ##

If you're only interested in the output of our parser(s), please check the [output](output) folder.  We have added parser output for release 2.1.0, 2.2.0 and 3.0.0. 

The [specific scores](Scores.md) are also available. If you want to add your scores to the table, consider doing a pull request.

## Author

* **Rik van Noord** - PhD-student at University of Groningen - [Personal website](http://www.rikvannoord.nl)

## Citation ##

This repository contains code and documentation for three semantic parsing papers.

For OpenNMT and Referee, please cite:

* Rik van Noord, Lasha Abzianidze, Antonio Toral and Johan Bos. **Exploring Neural Methods for Parsing Discourse Representation Structures.** TACL 2018 [\[PDF\]](https://www.aclweb.org/anthology/Q18-1043.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/Q18-1043.bib)

For Marian and linguistic feature extraction, please cite:

* Rik van Noord, Antonio Toral and Johan Bos. **Linguistic Information in Neural Semantic Parsing with Multiple Encoders.** IWCS 2019 [\[PDF\]](https://www.aclweb.org/anthology/W19-0504.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/W19-0504.bib)

For AllenNLP and DRS Jury, please cite:

* Rik van Noord, Antonio Toral and Johan Bos. (2020) **Character-level Representations Improve DRS-based Semantic Parsing Even in the Age of BERT.** EMNLP 2020

If you use Counter, please cite our:

* Rik van Noord, Lasha Abzianidze, Hessel Haagsma, and Johan Bos. **Evaluating scoped meaning representations**. LREC 2018 [\[PDF\]](https://www.aclweb.org/anthology/L18-1267.pdf) [\[BibTex\]](https://www.aclweb.org/anthology/L18-1267.bib)

If you use data from the PMB, please cite:

* Abzianidze, L., Bjerva, J., Evang, K., Haagsma, H., van Noord, R., Ludmann, P., Nguyen, D. & Bos, J **The Parallel Meaning Bank: Towards a Multilingual Corpus of Translations Annotated with Compositional Meaning Representations**, EACL 2017 [\[PDF\]](https://www.aclweb.org/anthology/E17-2039.pdf) [\[BibText\]](https://www.aclweb.org/anthology/E17-2039.bib)


## Acknowledgments

* Thanks to all members of the [Parallel Meaning Bank](http://pmb.let.rug.nl)
