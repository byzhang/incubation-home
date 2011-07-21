#!/usr/bin/env python

from graph import Graph, Task
import random
import redis
import time


class SGD(Graph):
    def __init__(self, graph_name, params):
        Graph.__init__(self, graph_name, 'full')
        # factors
        self.factor = params['factor']
        self.min_val = params['min_val']
        self.max_val = params['max_val']
        self.sgd_gamma = params['sgd_gamma']
        self.sgd_lambda = params['sgd_lambda']


    def create_new_tasks(self, tasks, results, pipe):
        new_inlinks = self._get_new_inlinks(tasks, pipe)
        new_tasks = {}
        timestamp = time.time()
        for t in tasks:
            for n in t.get_all_edges(self.r).keys():
                for i in new_inlinks[n]:
                    task = repr(Task(
                        {'node': i, 'edges': {}, 'create_time': timestamp}, self.graph))
                    if task in new_tasks:
                        new_tasks[task] += results[t.node]
                    else:
                        new_tasks[task] = results[t.node]
        return new_tasks


    def process_tasks(self, tasks):
        # TODO: riak version
        results = {}
        for task in tasks:
            results[task.node] = self.process_task(task)
        return results


    def create_nodes(self, task, r):
        nodes = {}
        nodes[task.node] = SGDNode(task.node, self.graph, self.factor, r)
        for t in task.edges.keys():
            nodes[t] = SGDNode(t, self.graph, self.factor, r)
        for t in nodes.values():
            t.createnx()
        return nodes


    def get_all_nodes(self, task, nodes, r):
        for t in task.get_all_edges(r).keys():
            if t in nodes:
                continue
            nodes[t] = SGDNode(t, self.graph, self.factor, r)
        return nodes


    def process_task(self, task):
        # TODO: run it in a separated process, need to create a new redis client
        nodes = self.create_nodes(task, self.r)
        nodes = self.get_all_nodes(task, nodes, self.r)
        user = nodes[task.node]
        old_rmse = user.get_rmse()
        rmse = 0
        delta = 0
        old_user_weights = list(user.get_weights())
        for t, v in task.get_all_edges(self.r).items():
            item = nodes[t]
            prediction = user.predict(item, self.min_val, self.max_val)
            if isinstance(v, str):
                v = eval(v)
            err = v['weight'] - prediction
            rmse += pow(err, 2)
            item.scale_add_weights(1 - self.sgd_gamma * self.sgd_lambda,
                    self.sgd_gamma * err, user.get_weights())
            user.scale_add_weights(1 - self.sgd_gamma * self.sgd_lambda,
                    self.sgd_gamma * err, item.get_weights())
            item.update()
        user.set_rmse(rmse)
        delta = user.compute_delta(old_user_weights)
        user.update()
        print 'node', task.node, 'rmse', old_rmse, '->', rmse
        return delta


class SGDNode(object):
    def __init__(self, name, graph, factor, r):
        # graph name, it's not included in value to save storage
        self.graph = graph
        # node name
        self.name = name
        # factor of svd
        self.factor = factor
        self.contents = {}
        self.r = r
        # redis hashset contains all the content of the node: vector, delta
        self.redis_key = 'graph.%s.SGD.%s' % (self.graph, self.name)


    def createnx(self):
        # TODO: create riak objects instead of redis objects
        self.r.hsetnx(self.redis_key, 'delta', 0)
        self.r.hsetnx(self.redis_key, 'weights', self.random_vector(self.factor))
        self.r.hsetnx(self.redis_key, 'rmse', 0)


    def predict(self, item, min_val, max_val):
        if self.factor != item.factor:
            return None
        user_weights = self.get_weights()
        item_weights = item.get_weights()
        prediction = 0
        for x in xrange(self.factor):
            prediction += user_weights[x] * item_weights[x]
        prediction = min(max_val, max(min_val, prediction))
        return prediction


    def random_vector(self, n):
        vector = []
        for i in xrange(n):
            vector.append(random.random() * 0.1)
        return vector


    def prepare_weights(self, weights):
        weights = eval(weights)
        weights.extend(self.random_vector(self.factor - len(weights)))
        return weights


    def get_weights(self):
        # only the first factor weights should be used.
        if len(self.contents) == 0:
            self.contents = self.r.hgetall(self.redis_key)
            self.contents['weights'] = self.prepare_weights(self.contents['weights'])
        return self.contents['weights']


    def get_rmse(self):
        if len(self.contents) == 0:
            self.contents = self.r.hgetall(self.redis_key)
            self.contents['weights'] = self.prepare_weights(self.contents['weights'])
        return self.contents['rmse']


    def set_rmse(self, rmse):
        self.contents['rmse'] = rmse


    def set_weights(self, weights):
        self.contents['weights'] = weights


    def set_delta(self, delta):
        self.contents['delta'] = delta


    def scale_add_weights(self, scale1, scale2, updates):
        # weights = scale1 * weights + scale2 * updates
        for i in xrange(self.factor):
            self.contents['weights'][i] *= scale1
            self.contents['weights'][i] += scale2 * updates[i]


    def compute_delta(self, old_user_weights):
        delta = 0
        for i in xrange(self.factor):
            delta += abs(self.contents['weights'][i] - old_user_weights[i])
        self.contents['delta'] = delta
        return delta


    def update(self):
        self.r.hmset(self.redis_key, self.contents)


