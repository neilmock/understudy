import sys
import unittest
import StringIO
from multiprocessing import Process
from understudy import Understudy, Result
from understudy.exceptions import NoUnderstudiesError
from understudy.decorators import understudy

from helper import wait_for
from helper import TEST_DB


def start_understudy(channel, queue=False):
    understudy = Understudy(channel, queue=queue, db=TEST_DB)
    understudy.start()

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

class TestDecorator(unittest.TestCase):
    def setUp(self):
        # fork the understudy
        self.p = Process(target=start_understudy, args=("test",))
        self.p.start()

    def tearDown(self):
        self.p.terminate()

    def test_logging(self):
        while True:
            try:
                job = LoggedJob()
                result = job.add(1,1)
                break
            except NoUnderstudiesError:
                pass

        actual_result = wait_for(result)

        self.assertEquals(result.log,
                          "Adding 1 to 1")

    def test_blocking_logging(self):
        capture = StringIO.StringIO()
        sys.stdout = capture

        while True:
            try:
                job = BlockingLoggedJob()
                result = job.add(1,1)
                break
            except NoUnderstudiesError:
                pass


        self.assertEquals(capture.getvalue(),
                          "Adding 1 to 1\n")

    def test_blocking(self):
        while True:
            try:
                job = BlockingJob()
                result = job.add(1,1)
                break
            except NoUnderstudiesError:
                pass

        self.assertEquals(int(result), 2)

    def test_queued(self):
        job = QueuedJob()
        result = job.add(1,1)

        p = Process(target=start_understudy,
                    args=("test_queue",),
                    kwargs={'queue': True})
        p.start()

        retval = result.check()
        while not retval:
            retval = result.check()

        p.terminate()

        self.assertEquals(int(retval), 2)

    def test_without_requirements(self):
        while True:
            try:
                job = Job()
                result = job.add(1,1)
                break
            except NoUnderstudiesError:
                pass

        self.assertTrue(isinstance(result, Result))

        actual_result = wait_for(result)

        self.assertEquals(actual_result, "2")

    def test_with_requirements(self):
        while True:
            try:
                job = JobWithRequirements()
                result = job.do_import()
                break
            except NoUnderstudiesError:
                pass

        self.assertTrue(isinstance(result, Result))

        actual_result = wait_for(result)

        self.assertEquals(actual_result, "True")
