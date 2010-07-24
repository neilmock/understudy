from understudy.decorators import understudy
from understudy import Understudy


TEST_DB = 15

def start_understudy(channel, queue=False):
    understudy = Understudy(channel, queue=queue, db=TEST_DB)
    understudy.start()

def wait_for(result):
    _result = result.check()
    while not _result:
        _result = result.check()

    return _result

class Job(object):
    @understudy("test", db=TEST_DB)
    def add(self, num1, num2):
        return num1 + num2

class LoggedJob(object):
    @understudy("test", db=TEST_DB)
    def add(self, num1, num2):
        self.logger.info("Adding %s to %s" % (num1, num2))
        return num1 + num2

class BlockingLoggedJob(object):
    @understudy("test", block=True, db=TEST_DB)
    def add(self, num1, num2):
        self.logger.info("Adding %s to %s" % (num1, num2))
        return num1 + num2

class BlockingJob(object):
    @understudy("test", block=True, db=TEST_DB)
    def add(self, num1, num2):
        return num1 + num2

class QueuedJob(object):
    @understudy("test_queue", queue=True, db=TEST_DB)
    def add(self, num1, num2):
        return num1 + num2

class JobWithRequirements(object):
    @understudy("test", db=TEST_DB, packages=['boto>=1.9b'])
    def do_import(self):
        try:
            import boto
            return True
        except ImportError, e:
            return e

