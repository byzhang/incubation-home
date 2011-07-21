#!/bin/bash

./ShrinkNgram.py --type cn --min_freq $2 --max_ngram $3 data/raw_ngram/$1.cn > data/ngram/$1.$2.$3.cn
./ShrinkNgram.py --type en --min_freq $2 --max_ngram $3 data/raw_ngram/$1.en > data/ngram/$1.$2.$3.en
