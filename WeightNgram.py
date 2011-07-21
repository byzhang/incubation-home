#!/usr/bin/env python
# -*- coding:UTF-8 -*-

from optparse import OptionParser
import codecs
import heapq
import math
import utils


def main():
    parser = OptionParser(conflict_handler='resolve')
    parser.add_option('--ngram', default='', help='ngram file')
    parser.add_option('--ngram_count', default='', help='ngram count')
    parser.add_option('--noise', default='', help='noise ngram file')
    parser.add_option('--noise_count', default='', help='noise ngram count')
    (options, args) = parser.parse_args()
    ngram_count = float(options.ngram_count)
    noise_count = float(options.noise_count)

    iters = (
            utils.NgramIter1(codecs.open(options.ngram, encoding='utf-8', mode='r'), True),
            utils.NgramIter2(codecs.open(options.noise, encoding='utf-8', mode='r'), True))
    l = apply(heapq.merge, tuple(iters))
    cur_ngram = ''
    cur_count1 = 0
    cur_count2 = 0
    for ngram, source, count in l:
        if cur_ngram == '' or cur_ngram == ngram:
            cur_ngram = ngram
            if source == '1':
                cur_count1 = int(count)
            else:
                cur_count2 = int(count)
            continue
        if ngram != cur_ngram:
            if cur_count1 != 0:
                if cur_count2 == 0:
                    cur_count2 = 1
                weight = cur_count1 * math.log(noise_count / ngram_count * cur_count1 / cur_count2)
                if weight > 0:
                    print cur_ngram.encode('utf-8'), weight
            cur_ngram = ngram
            if source == '1':
                cur_count1 = int(count)
                cur_count2 = 0
            else:
                cur_count2 = int(count)
                cur_count1 = 0
    if cur_count1 != 0:
        if cur_count2 == 0:
            cur_count2 = 1
        weight = cur_count1 * math.log(noise_count / ngram_count * cur_count1 / cur_count2)
        if weight > 0:
            print cur_ngram.encode('utf-8'), weight
    return


if __name__ == '__main__':
    main()
