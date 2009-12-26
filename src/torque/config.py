#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Command line options.
"""

# how torque is running
define('port', default=8090, help='which port to run on')
define('address', default='http://localhost', help='address server is running on')
define('base_task_url', default='http://localhost:8080', help='expand relative task urls')
define('queue_name', default='default_taskqueue', help='target queue')

# internals
define('max_tasks', default=5, help='how many tasks can be processed concurrently?')
define('min_delay', default=0.2, help='wait between polling when tasks pending')
define('max_empty_delay', default=1.6, help='wait when there are no tasks pending')
define('max_error_delay', default=240, help='wait when concurrent executer is erroring')
define('empty_multiplier', default=2.0, help='multiply the delay by when empty')
define('error_multiplier', default=4.0, help='multiply the delay by when erroring')
define('max_task_errors', default=100, help='how many times can a task error?')
define('max_task_delay', default=1800, help='longest an erroring task can be delayed for')