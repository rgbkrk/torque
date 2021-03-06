#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tornado web application.
  
  Provides:
  
  * ``/add_task``
  * ``/concurrent_executer``
  
  Run using::
      
      $ ./bin/torque-serve
  
  Add ``--help`` to see the configuration options.
"""

import logging
import math
import time

from tornado import ioloop, httpclient, httpserver, web
from tornado import options as tornado_options
from tornado.options import define, options
from tornado.escape import json_decode, json_encode

define('debug', default=False, help='debug mode')
define('port', default=8889, help='port to run on')
define(
    'processes', default=1, 
    help='how many processes to spawn (use 0 for one per CPU)'
)
define(
    'request_timeout', default=20.0,
    help='how long to allow tasks to be processed for before timing out'
)

from client import add_task, fetch_tasks, count_tasks
from utils import do_nothing, unicode_urlencode

class AddTask(web.RequestHandler):
    """Add tasks to the queue over an http request, i.e.: from any
      programming language.
      
      To add a task to the queue, post to this handler with two params:
      
      * ``url`` which is the url to the webhook you want the task to request
      * ``params`` which is a json encoded dictionary of the params you want
      to post to the webhook you're requesting
      
      You can also provide a ``delay`` and a ``queue_name``.
    """
    
    def get(self):
        self.post()
    
    def post(self):
        # url is required
        url = self.get_argument('url')
        # params are passed in empty if not provided
        kwargs = {
            'params': json_decode(self.get_argument('params', '{}')),
        }
        # queue_name and delay are optional
        queue_name = self.get_argument('queue_name', False)
        if queue_name:
            kwargs['queue_name'] = queue_name
        delay = self.get_argument('delay', False)
        if delay:
            kwargs['delay'] = delay
        return add_task(url, **kwargs)
    


class ConcurrentExecuter(web.RequestHandler):
    """Takes a ``queue_name``, fetches ``limit`` items from the queue, 
      and posts them individually via concurrent, non-blocking requests.
      
      This means that you can execute ``limit`` tasks in the time it
      takes the longest to complete.
      
      If the queue is empty, we return ``204`` to indicate there's no content 
      to process.  Unless the ``check_pending`` argument has been provided 
      and is ``True``, at which point it checks the queue to see if any tasks 
      are pending and if none are, returns ``205`` to indicate that the queue
      has been completely emptied.
      
      By returning status codes, the ``ConcurrentExecuter`` delegates
      responsibility for deleting or rescheduling tasks.  It just executes
      them... concurrently.
    """
    
    def get(self):
        self.post()
    
    @web.asynchronous
    def post(self):
        # queue_name and limit are optional
        kwargs = {}
        queue_name = self.get_argument('queue_name', False)
        limit = self.get_argument('limit', False)
        if queue_name:
            kwargs['queue_name'] = queue_name
        if limit:
            kwargs['limit'] = limit
        tasks = fetch_tasks(**kwargs)
        len_tasks = len(tasks)
        if len_tasks == 0:
            self.set_status(204)
            check_pending = self.get_argument('check_pending')
            if not isinstance(check_pending, bool):
                check_pending = eval(check_pending)
            if check_pending:
                kwargs = queue_name and {'queue_name': queue_name} or {}
                if count_tasks(**kwargs) < 1:
                    self.set_status(205)
            self.finish()
        else:
            # maintain a list of ids, which we pop from in _handle_response
            # so that we know when we're done
            self.task_ids = []
            # build a dict of {task_id: status_code, ...} for each task
            # to return as the response
            self.status_codes = {}
            http = httpclient.AsyncHTTPClient(max_clients=len_tasks)
            for task in tasks:
                callback = self.async_callback(self._handle_response, task_id=task.id)
                kwargs = {}
                if task.params:
                    kwargs = {
                        'method': 'POST',
                        'body': unicode_urlencode(task.params)
                    }
                if options.request_timeout:
                    kwargs['request_timeout'] = options.request_timeout
                http.fetch(task.url, callback=callback, **kwargs)
                self.task_ids.append(task.id)
            
        
    
    def _handle_response(self, response, task_id):
        # remove the task from the pending list
        self.task_ids.remove(task_id)
        # store the response status code against the task id
        self.status_codes[task_id] = response.code
        # if all the tasks have returned
        if len(self.task_ids) == 0:
            self.set_status(200)
            self.write(self.status_codes)
            self.finish()
        
    
    


mapping = [(
        r'/add_task', 
        AddTask,
    ), (
        r'/concurrent_executer', 
        ConcurrentExecuter
    )
]

def serve():
    # create the web application
    application = web.Application(mapping, debug=options.debug)
    # start the http server
    http_server = httpserver.HTTPServer(application)
    http_server.bind(options.port)
    if options.processes > 0:
        http_server.start(options.processes)
    else: # fork one process per cpu
        http_server.start()
    # start the async ioloop
    ioloop.IOLoop.instance().start()
    


def main():
    # hack around an OSX error
    tornado_options.enable_pretty_logging = do_nothing
    # parse the command line options
    tornado_options.parse_command_line()
    # serve the webapp
    serve()


if __name__ == "__main__":
    main()

