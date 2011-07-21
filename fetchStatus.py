#!/usr/bin/env python

from optparse import OptionParser
import hashlib
import redis
import time
import utils


def main():
    parser = OptionParser(conflict_handler='resolve')
    parser.add_option('--source', default='public', help='friends|public')
    parser.add_option('--pages', default='1', help='')
    parser.add_option('--userid', default='9', help='')
    (options, args) = parser.parse_args()
    if len(args) == 0:
        args.append('0')

    fetcher = utils.Weibo()
    if options.userid == '':
        if options.source == 'friends':
            print 'must specify userid to fetch friends'
            return
        fetcher.initAPI()
    else:
        fetcher.setToken(int(options.userid))

    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)

    md5_key = '%s-md5' % options.source
    id_key = '%s-id' % options.source

    sleep_time = 1.0
    pages = int(options.pages)
    while True:
        texts = []

        try:
            if options.source == 'public':
                print 'fetching', pages, 'pages'
                texts = fetcher.public_timeline(pages=pages)
            elif options.source == 'friends':
                print 'fetching', pages, 'pages'
                texts = fetcher.friends_timeline(pages=pages)
            else:
                print 'wrong source', options.source
                return
        except Exception, e:
            print args[0], e
            sleep_time += 1
            print args[0], 'sleeping', sleep_time
            time.sleep(sleep_time)
            continue

        num_text = 0
        for text in texts:
            md5 = hashlib.md5(text.encode('utf-8')).hexdigest()

            while True:
                r.watch(md5_key)
                r.watch(id_key)

                has_text = r.sismember(md5_key, md5)
                if has_text:
                    r.unwatch()
                    # break, and process next text
                    break

                id = r.get(id_key)
                if id == None:
                    id = 0
                else:
                    id = int(id) + 1

                pipe = r.pipeline()
                pipe = pipe.sadd(md5_key, md5).set(id_key, id)
                pipe = pipe.set('%s-%d' % (options.source, id), text)
                try:
                    response = pipe.execute()
                    if not response[-1]:
                        print args[0], 'race condition: %d %s %s' % (id, text, md5)
                        # break, and process next text
                        break
                except redis.exceptions.WatchError, e:
                    # retry this text
                    print args[0], 'retry', id
                    pass
                else:
                    # break, and process next text
                    num_text += 1
                    break

        if num_text < 160:
            sleep_time += 1
        else:
            sleep_time = max(1, sleep_time/2)
        print args[0], 'fetched', num_text
        if sleep_time > 1:
            print args[0], 'sleeping', sleep_time
        time.sleep(sleep_time)
        pages = min(num_text / 160 + 1, num_text / 200 + 2)


if __name__ == '__main__':
    main()
