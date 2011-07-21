#!/bin/bash

./MergeNgram.py --type $1 $2*.$1 > $3.$1
mv $2*.$1 $4/
mv $3.$1 $2.$1

