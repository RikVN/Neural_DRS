# Semtag analysis #

In our EMNLP paper, we introduced the idea of analysis by [semtags](https://www.aclweb.org/anthology/W17-6901.pdf). Based on the semtags in a sentence, we can select subsets of sentences that contain a certain semantic or linguistic phenomena. This allows us to compare model performance across these phenomea, giving us more insight in their respective qualities. 

We experimented on DRS parsing, but this works for any NLP task that has a sentence as input and a single score per sentence as output!

## How does it work? ##

Say we are interested in how well a model does on sentence containing a negation. We select all sentences that contain the semtag NOT and calculate accuracy of the model on just those sentences. Similarly, we can be interested in how well the model does on sentences that contain a logical operator. For this phenomenon, we select all sentences that contain at least one out of this set of semtags: ALT, XCL, DIS, AND, IMP, BUT. This is the list of phenomena we pre-selected:

<pre>
Modal          : NOT, NEC, POS
  Negation     : NOT
  Possibility  : POS
  Necessity    : NEC
Logic          : ALT, XCL, DIS, AND, IMP, BUT
Pronouns       : PRO, HAS, REF, EMP
Attributes     : QUC, QUV, COL, IST, SST, PRI, DEG, INT, REL, SCO
Comparatives   : EQU, APX, MOR, LES, TOP, BOT, ORD
Named Entities : PER, GPE, GPO, GEO, ORG, ART, HAP, UOM, CTC, LIT, NTH
Numerals       : QUC, MOY, SCO, ORD, DAT, DOM, YOC, DEC, CLO
</pre>

You can set up your own experiments by altering get_semtag_exps() in semtag_analysis.py.

The script first prints all scores per individual semtag, after which the phenomena scores are printed.

## Running with PMB data ##

If you use PMB data, you can just use our extracted CoNLL files with gold semtag information. Likely, you can also use [DRS Jury](DRS_jury.md) to get these scores. 

If you want to run the script separately, this is an example on the dev set of 3.0.0:

```
python src/semtag_analysis.py --semtag_file DRS_parsing/parsing/layer_data/gold/en/dev.conll --result_files output/pmb-3.0.0/en/dev/bert_only/output1.idv output/pmb-3.0.0/en/dev/bert_char_1enc/output1.idv --names bert_only bert_char_1enc -c
```

The argument -c was needed to tell the script that semtag information was added in PMB CoNLL format. Here, the result files contained a single F-score on each line, which were averaged. However, this gives a macro F1 score, while we usually calculate a micro F1 score. To calculate this, specify the matched, produced and gold clauses on each line (in this order!) in the result files. This is the calculation as performed by DRS Jury. Use -m to tell the script to interpret the input correctly.

```
python src/semtag_analysis.py --semtag_file DRS_parsing/parsing/layer_data/gold/en/dev.conll --result_files output/pmb-3.0.0/en//dev/bert_only/output1.prf output/pmb-3.0.0/en//dev/bert_char_1enc/output1.prf  --names bert_only bert_char_1enc -c -m
```

## Running on a new task ##

It is also possible to run this analysis on a new task, with sentences that are not in the PMB! Note that there are no gold standard semtags available, meaning we have to parse the sentences with a semtagger. I added an easy to install, train and parse with CRF semtagger to this repository.

First, install the requirements:

```
pip install scikit-learn sklearn_crfsuite joblib
```

Then, we train a CRF-tagger model on the gold English training data of 3.0.0. Should obtain 94.3% accuracy on the dev set.

```
python src/crf_tagger.py -o train --train_file DRS_parsing/parsing/layer_data/gold/en/train.conll --test_file DRS_parsing/parsing/layer_data/gold/en/dev.conll --model semtag.model
```

This model can then be used to parse your (tokenized!) sentences. To test if it works, I've randomly selected 100 sentences from the AMR training set:

```
python src/crf_tagger.py -o parse --test_file output/semtag_test/sentences.tok -m semtag.model -out output/semtag_test/sentences.sem
```

I've also added two files with random 100 scores, so we can see how to run the analyis:

```
python src/semtag_analysis.py -s output/semtag_test/sentences.sem -r output/semtag_test/rand1.txt output/semtag_test/rand2.txt --names rand1 rand2
```

Of course these scores are meaningless, but the output should look like this:

<pre>
Exp            	Docs 	rand1  	rand2  
All            	100  	50.110 	45.480 
Modal          	40   	48.025 	50.525 
  Negation     	27   	50.741 	51.519 
  Possibility  	15   	50.733 	51.867 
  Necessity    	11   	47.636 	45.818 
Logic          	60   	49.517 	45.417 
Pronouns       	64   	51.047 	49.672 
Attributes     	91   	50.934 	44.516 
Comparatives   	3    	43.333 	17.000 
Named Entities 	54   	47.000 	43.981 
Numerals       	12   	51.167 	31.750
</pre>

Hopefully, this allows for a more detailed analysis of your system(s). If you run into any problems, feel free to open an issue or email me.
