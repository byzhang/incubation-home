#!/usr/bin/env python

import redis
import time


class Task(object):
    def __init__(self, value, graph):
        # graph name, it's not included in value to save storage
        self.graph = graph
        # node name
        self.node = value['node']
        # edges is the dict: {target -> {'weight', 'op'}}
        self.edges = value['edges']
        # create time of edges, instead of all_edges, allowing multiple tasks on one node
        self.create_time = value['create_time']
        # the same data structure with self.edges
        self.all_edges = {}
        # redis hashset contains all the outlinks of the node, i.e. all_edges
        self.redis_outlink_key = 'graph.%s.outlink.%s' % (self.graph, self.node)


    def __repr__(self):
        value = {
                'node': self.node,
                'create_time': self.create_time,
                'edges': self.edges}
        return repr(value)


    def get_all_edges(self, r):
        if len(self.all_edges) > 0:
            return self.all_edges
        self.all_edges = r.hgetall(self.redis_outlink_key)
        for x, y in self.edges.items():
            if x not in self.all_edges:
                self.all_edges[x] = y
                continue
            if y['op'] == 'r':
                self.all_edges[x] = y
            elif y['op'] == 'a':
                self.all_edges[x]['weight'] += y['weight']
            else:
                self.all_edges[x]['weight'] *= float(y['op'])
                self.all_edges[x]['weight'] += y['weight']
        return self.all_edges


    def set_all_edges(self, pipe):
        # should always call after get_all_edges
        if len(self.all_edges) == 0:
            return
        pipe.hmset(self.redis_outlink_key, self.all_edges)


def LoadTask(string, graph):
    value = eval(string)
#    value['edges'] = eval(value['edges'])
#    value['create_time'] = eval(value['create_time'])
    task = Task(value, graph)
    return task


class Graph(object):
    # single thread
    def __init__(self, graph_name, consistency):
        # used to generate redis key and riak path
        self.graph = graph_name
        # 'node', 'directed_edge', 'undirected_edge', 'full'
        self.consistency = consistency
        # list of Tasks
        self.available_tasks = []
        # set of node names
        self.locked_nodes = set()
        pool = redis.ConnectionPool(host='localhost', port=6379, db=1)
        self.r = redis.Redis(connection_pool=pool)
        # redis sorted set of repr of tasks
        self.redis_task_key = 'graph.%s.tasks' % self.graph


    def _lock_redis(self, key, pri):
        lock_key = 'lock-%s' % key
        lock = self.r.setnx(lock_key, pri)
        if lock == 0:
            while not lock:
                time.sleep(pri)
                lock = self.r.setnx(lock_key, pri)


    def _unlock_redis(self, key):
        lock_key = 'lock-%s' % key
        self.r.delete(lock_key)


    def add_tasks(self, values):
        timestamp = time.time()
        tasks = {}
        for v in values:
            task = repr(Task({'node': v['node'], 'edges': v['edges'], 'create_time': timestamp}, self.graph))
            tasks[task] = v['score']
        self._lock_redis(self.redis_task_key, 2)
        self.r.zadd(self.redis_task_key, **tasks)
        self._unlock_redis(self.redis_task_key)


    def _get_new_inlinks(self, tasks, pipe):
        nodes = []
        for t in tasks:
            nodes.append(t.node)
        # dict: {node_name -> set(node_name)}
        new_inlinks = {}
        # fetch existing inlinks
        for t in tasks:
            for n in t.get_all_edges(self.r).keys():
                if n in new_inlinks:
                    continue
                # a redis set of names of inlink nodes
                key = 'graph.%s.inlink.%s' % (self.graph, n)
                inlinks = self.r.smembers(key)
                new_inlinks[n] = inlinks
        # update with new inlinks
        for t in tasks:
            for n in t.edges.keys():
                new_inlinks[n].add(t.node)
                # redis set of inlink node name
                key = 'graph.%s.inlink.%s' % (self.graph, n)
                pipe.sadd(key, t.node)
        return new_inlinks


    def lock_nodes_for_mapreduce(self, task):
        self.locked_nodes.add(task.node)
        if self.consistency == 'undirected_edge' or self.consistency == 'full':
            for linked_node in task.get_all_edges(self.r).keys():
                self.locked_nodes.add(linked_node)


    def get_top_task(self):
        while len(self.available_tasks) > 0:
            task = self.available_tasks.pop()
            if self.consistency == 'node':
                self.lock_nodes_for_mapreduce(task)
            elif self.consistency == 'undirected_edge':
                if task.node in self.locked_nodes:
                    continue
                self.lock_nodes_for_mapreduce(task)
            elif self.consistency == 'directed_edge':
                # TODO: implement the consistency check
                self.lock_nodes_for_mapreduce(task)
            elif self.consistency == 'full':
                if task.node in self.locked_nodes:
                    continue
                has_conflict = False
                for linked_node in task.get_all_edges(self.r).keys():
                    if linked_node in self.locked_nodes:
                        has_conflict = True
                        break
                if has_conflict:
                    continue
                self.lock_nodes_for_mapreduce(task)
            return task
        return None


    def init_available_tasks(self):
        self._lock_redis(self.redis_task_key, 1)
        topk = self.r.zrange(self.redis_task_key, 0, 2000)
        self._unlock_redis(self.redis_task_key)
        self.available_tasks = [LoadTask(x, self.graph) for x in topk]


    def create_new_tasks(self, tasks, results, pipe):
        # Pure virtual
        pass


    def complete_tasks(self, tasks, results):
        pipe = self.r.pipeline()

        # update outlinks
        for t in tasks:
            t.set_all_edges(pipe)

        # remove completed tasks from tasks
        keys = [repr(t) for t in tasks]
        pipe.zrem(self.redis_task_key, *keys)

        # append more tasks from the completed ones based on the algorithm
        new_tasks = self.create_new_tasks(tasks, results, pipe)
        pipe.zadd(self.redis_task_key, value=None, score=None, **new_tasks)

        self._lock_redis(self.redis_task_key, 1)
        while True:
            try:
                pipe.execute()
            except redis.exceptions.WatchError, e:
                print e
                pass
            else:
                break
        self._unlock_redis(self.redis_task_key)


    def process_tasks(self, tasks):
        # pure virtual
        pass


    def process(self):
        self.init_available_tasks()
        self.locked_nodes = set()

        tasks = []
        while True:
            task = self.get_top_task()
            if task == None:
                break
            print 'adding task', task.node
            tasks.append(task)

        results = self.process_tasks(tasks)

        self.complete_tasks(tasks, results)


