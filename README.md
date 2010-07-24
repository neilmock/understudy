Understudy
==========

Understudy is a framework for distributed computing in Python.  It allows
you to write Python code and transparently execute it on any number of
listening nodes.

It requires the 2.0 version of Redis with pub/sub support.

Whirlwind Tour
--------------

Fire up a redis server, either locally or on a remote node. Install
Understudy (PyPi coming soon).

Run this script:

    from understudy import Understudy

    understudy = Understudy("calculator")
    understudy.start()

The Understudy constructor takes all the keyword params of the Redis
client, in case you need specific host/port/db.

Elsewhere, define this class (for instance, in arithmetic.py):

    from understudy.decorators import understudy

    class Adder(object):
        @understudy("calculator")
        def add(self, num1, num2):
            return num1 + num2

The "understudy" decorator also takes standard Redis client keywords arguments.

In a repl:

    >>> from arithmetic import Adder
    >>> adder = Adder()
    >>> result = adder.add(1,1)
    >>> result.check()
    None
    >>> # wait for task to finish
    ...
    >>> result.check()
    '2'

Voila, addition performed on the remote node with the result returned locally.

Virtual Environments
--------------------

Understudy has built-in support for virtual environments (via virtualenv).
Packages can be specified in the decorator to be installed in a virtual
environment prior to execution.

    from understudy.decorators import understudy

    class TimeZoneTool(object):
        @understudy(packages=["pytz"], block=True)
        def eastern(self):
            from pytz import timezone
            eastern = timezone('US/Eastern')

            return eastern.zone

At the REPL:

    >>> tzt = TimeZoneTool()
    >>> tzt.eastern()
    US/Eastern

Notice the "block" keyword argument?  In the previous example, a
Result object was returned immediately upon method invocation, and
the result could be polled.  If "block" is set to True, the method
will block until remote execution has finished and the result is available.

Logging
-------

Understudy has built-in support for logging during the remote execution
of methods.

    class Adder(object):
        @understudy("calculator")
        def add(self, num1, num2):
            self.logger.info("Adding %s to %s" % (num1, num1))
            return num1 + num2

If blocking is enabled, logging will take place on stdout;
otherwise, the Result object will be populated with the contents of the
log (populated along with the result during the check() method).

    >>> result.check()
    '2'
    >>> result.log
    'Adding 1 to 1'

Disclaimer
----------

This project is "alpha" and is subject to drastic change, including breaking
of API compabilitiy.

Also, this really does execute Python code remotely on any listening node.
Please use with caution and secure your servers.