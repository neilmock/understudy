Understudy
==========

Understudy is a framework for distributed computing in Python.  It allows
you to write Python code and transparently execute it on any number of
listening nodes.

Overview
--------

Understudy provides a decorator for enabling Python classes to
distribute work to an understudy:

    class Job(object):
        @understudy("calculator")
        def add(self, num1, num2):
            return num1 + num2

The "understudy" decorator takes an understudy name as the first argument.
This essentially sends the method to a named understudy process that is
listening for requests.

Here's an example of starting an understudy:

    understudy = Understudy("calculator")
    understudy.start()

These will typically run daemonized on compute nodes.

Example
-------

Continuing the example above, here's how to add two numbers:

    >>> job = Job()
    >>> result = job.add(1,1)
    >>> result.check()
    None
    >>> result.check()
    2

The add() method immediately returns a Result class, from which the result
store can be polled and ultimately returned with a value.  "None" is returned
if the understudy has not yet completed the task.

Virtual Environments
--------------------

Understudy requires that all imports used in the module are available on
the Python environment of the understudy node(s).

To facilitate this, Understudy has support for automatically bootstrapping
a virtual environment and executing the called method within the context of
that environment.

Here's an example:

    from understudy.decorators import understudy
    from boto.s3 import Connection

    class Downloader(object):
        @understudy("s3_understudy", packages=['boto>=1.9b'])
        def download(key):
            connection = Connection()
            key = connection.get_bucket("mybucket").get_key(key)
            key.get_contents_to_filename("/path/to/myfile")

This bootstraps a virtual environment on the understudy node by installing
boto via PIP before executing the download() method.  Packages are defined
in PIP requirements.txt fashion.

Redis
-----

Understudy is built on Redis, and both the decorator and the Understudy
constructor take standard redis-py connection parameters as arguments:

    class Job(object):
        @understudy("calculator", host="127.0.0.1", port=6332, db=12)
        def add(self, num1, num2):
            return num1 + num2

Disclaimer
----------

This is a work in progress and should be considered alpha as in
"please dont use" until further notice.