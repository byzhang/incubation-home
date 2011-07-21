#!/usr/bin/env python

import redis
import sgd


def generate_values(inputs):
    values = {}
    for input in inputs:
        (x, y, weight) = input.split()
        if x not in values:
            value = {'node': x,
                    'edges': {},
                    'score': 1000}
            values[x] = value
        values[x]['edges'][y] = {'weight': float(weight), 'op': 'a'}
    return values.values()


def main():
    graph_name = 'test'
    pool = redis.ConnectionPool(host='localhost', port=6379, db=1)
    r = redis.Redis(connection_pool=pool)
    # clean test graph
    keys = r.keys('*graph.%s.*' % graph_name)
    if len(keys) > 0:
        r.delete(*keys)

    # generate tasks
    params = {}
    params['factor'] = 3
    params['min_val'] = 1
    params['max_val'] = 3
    params['sgd_gamma'] = 1e-2
    params['sgd_lambda'] = 0.3
    g = sgd.SGD(graph_name, params)
    g.add_tasks(generate_values(['0 3 1', '1 3 2', '2 3 3', '2 4 1', '0 5 2', '1 5 3', '2 5 1']))

    # process tasks
    while (r.zcard('graph.%s.tasks' % graph_name) > 0):
        print 'a new step'
        g.process()
#        break

    # print results


if __name__ == '__main__':
    main()
