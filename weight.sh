#!/bin/bash

NGRAM="data/ngram/$1.en"
NGRAM_COUNT=`tail -1 $NGRAM | grep ALLCOUNT | cut -d ' ' -f 2`
echo $NGRAM_COUNT

NOISE="data/ngram/$2.en"
NOISE_COUNT=`tail -1 $NOISE | grep ALLCOUNT | cut -d ' ' -f 2`
echo $NOISE_COUNT

OUTPUT="data/ngram/$1.weight.en"

./WeightNgram.py --ngram $NGRAM --ngram_count $NGRAM_COUNT --noise $NOISE --noise_count $NOISE_COUNT > $OUTPUT

NGRAM="data/ngram/$1.cn"
NGRAM_COUNT=`tail -1 $NGRAM | grep ALLCOUNT | cut -d ' ' -f 2`
echo $NGRAM_COUNT

NOISE="data/ngram/$2.cn"
NOISE_COUNT=`tail -1 $NOISE | grep ALLCOUNT | cut -d ' ' -f 2`
echo $NOISE_COUNT

OUTPUT="data/ngram/$1.weight.cn"

./WeightNgram.py --ngram $NGRAM --ngram_count $NGRAM_COUNT --noise $NOISE --noise_count $NOISE_COUNT > $OUTPUT

