#!/usr/bin/env python

# Just run a single instance

from optparse import OptionParser
import hashlib
import io
import os
import redis
import time
import utils


def main():
    parser = OptionParser(conflict_handler='resolve')
    parser.add_option('--source', default='public', help='friends|public, used as filename prefix as well')
    parser.add_option('--raw', default='', help='folder of raw ngram files')
    parser.add_option('--merge', default='', help='folder of merged ngram files')
    parser.add_option('--backup', default='', help='backup folder for raw ngram files')
    parser.add_option('--min_ngram', default='', help='')
    parser.add_option('--max_ngram', default='', help='')
    parser.add_option('--min_freq', default='', help='')
    (options, _) = parser.parse_args()
    min_ngram = int(options.min_ngram)
    max_ngram = int(options.max_ngram)
    min_freq = int(options.min_freq)
    raw_file = '/'.join((options.raw, options.source))
    merged_file = '/'.join((options.merge, options.source))
    min_process_size = 10000
    if options.source == 'friends':
        min_process_size = 1000
    min_merge_size = 4000000
    if options.source == 'friends':
        min_merge_size = 400000

    segmenter = utils.StatusSegmenter()
    cleaner = utils.Cleaner()

    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)

    md5_key = '%s-segment-md5' % options.source
    id_key = '%s-ngram-id' % options.source
    text_key = '%s-id' % options.source

    num_ngram = 0
    sleep_time = 1.0
    while True:
        cn_ngrams = {}
        en_ngrams = {}
        processed_md5 = []

        while True:
            r.watch(id_key)
            r.watch(md5_key)

            # get start_id, end_id
            start_id = r.get(id_key)
            if start_id == None:
                start_id = '0'
            end_id = r.get(text_key)
            start = int(start_id)
            end = min(start + 40000, int(end_id))

            # get keys and status
            if end - start < min_process_size:
                r.unwatch()
                sleep_time += 1
                time.sleep(sleep_time)
                continue
            sleep_time = max(1, sleep_time/2)
            keys = ['%s-%d' % (options.source, x) for x in xrange(start, end)]
            print 'processing', start, end
            lines = r.mget(keys)

            for line in lines:
                if line == None:
                    continue
                line = utils.ExtractText(line, options.source)
#                print 'LINE', line.encode('utf-8')
                texts = segmenter.segment(line)
                for text in texts:
                    # process each segment
                    text = text.strip()
#                    print 'SEGMENT', text.encode('utf-8')
                    md5 = hashlib.md5(text.encode('utf-8')).hexdigest()
                    if md5 in processed_md5:
                        continue
                    processed_md5.append(md5)
                    if r.sismember(md5_key, md5):
                        continue

                    sentences = cleaner.clean(text)
                    for s in sentences:
                        # process each sentence in en or in cn
                        s = s.strip()
                        if s == u'':
                            continue
#                        print 'SENTENCE', s.encode('utf-8')
                        if utils.IsEn(s[0]):
                            tokens = s.split()
                            utils.GenerateNgrams(tokens, min_ngram, max_ngram, u' ', en_ngrams)
                        else:
                            utils.GenerateNgrams(s, min_ngram, max_ngram, '', cn_ngrams)

            # generate en/cn ngrams
            keys = en_ngrams.keys()
            keys.sort()
            en_file = raw_file + start_id + '.en'
            en_output = io.open(en_file, mode='w', encoding='utf-8')
            for key in keys:
                en_output.write(u'%s %d\n' % (key, en_ngrams[key]))
            num_ngram += len(en_ngrams)

            keys = cn_ngrams.keys()
            keys.sort()
            cn_file = raw_file + start_id + '.cn'
            cn_output = io.open(cn_file, mode='w', encoding='utf-8')
            for key in keys:
                cn_output.write(u'%s %d\n' % (key, cn_ngrams[key]))
            num_ngram += len(cn_ngrams)

            # update redis
            pipe = r.pipeline()
            pipe.set(id_key, end)
            for md5 in processed_md5:
                pipe.sadd(md5_key, md5)
            try:
                pipe.execute()
            except redis.exceptions.WatchError, e:
                # retry this text
                print 'retry'
                pass
            else:
                # break, and process next text
                print 'complete processing'
                break

        # trigger merge
        if num_ngram > min_merge_size:
            print 'merging', num_ngram
            os.system('./merge.sh en %s %s %s' % (raw_file, merged_file, options.backup))
            os.system('./merge.sh cn %s %s %s' % (raw_file, merged_file, options.backup))
            print 'complete merge'
            lock = r.setnx('lock-for-weight.sh', options.source)
            if lock == 0:
                while not lock:
                    print 'waiting for lock weight.sh'
                    time.sleep(30)
                    lock = r.setnx('lock-for-weight.sh', options.source)
            print 'get lock for weight.sh'
            print 'shrinking', num_ngram
            os.system('./shrink.sh %s %d %d' % (options.source, min_freq, max_ngram))
            print 'complete shrink'
            if options.source == 'friends':
                print 'weighting', num_ngram
                os.system('./weight.sh friends.%d.%d public.%d.%d' % (min_freq, max_ngram, min_freq, max_ngram))
                print 'complete weight'
            r.delete('lock-for-weight.sh')
            num_ngram = 0


if __name__ == '__main__':
    main()
