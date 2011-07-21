#!/usr/bin/env python

from optparse import OptionParser
from weibopy.error import WeibopError
import hashlib
import redis
import time
import utils


def main():
    parser = OptionParser(conflict_handler='resolve')
    parser.add_option('--userid', default='9', help='')
    parser.add_option('--init', default='0', help='')
    (options, args) = parser.parse_args()

    friender = utils.Weibo()
    friender.setToken(int(options.userid))

    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)

    key = 'followed-by-%s' % options.userid

    pipe = r.pipeline()
    followed = set()
    if options.init == '0':
        followed = r.smembers(key)
    else:
        users = friender.friends()
        for user in users:
            user = user.encode('utf-8')
            pipe.sadd(key, user)
            followed.add(user)
    to_follow = r.zrevrange('orig-authors', 0, 2000)

    for x in to_follow:
        if x in followed:
            print 'skipping', x
            continue
        print 'adding', x

        err = ''
        try:
            friender.follow(x)
        except WeibopError, e:
            err = e.__str__()
            print err
        if 'already followed' in err or err == '':
            followed.add(x)
            pipe.sadd(key, x)
            continue
        if 'rate limit' in err or 'error_code:400,40028:hi' in err:
#            time.sleep(3600)
            break

    response = pipe.execute()


if __name__ == '__main__':
    main()
