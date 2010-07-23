import unittest
from multiprocessing import Process
from understudy import Understudy, Result
from understudy.exceptions import NoUnderstudiesError
from understudy.decorators import understudy

from helper import TEST_DB


def start_understudy(channel):
    understudy = Understudy(channel, db=TEST_DB)
    understudy.start()

class Job(object):
    @understudy("test", db=TEST_DB)
    def add(self, num1, num2):
        return num1 + num2

class BlockingJob(object):
    @understudy("test", block=True, db=TEST_DB)
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

    def test_blocking(self):
        while True:
            try:
                job = BlockingJob()
                result = job.add(1,1)
                break
            except NoUnderstudiesError:
                pass

        self.assertEquals(int(result), 2)

    def test_without_requirements(self):
        while True:
            try:
                job = Job()
                result = job.add(1,1)
                break
            except NoUnderstudiesError:
                pass

        self.assertTrue(isinstance(result, Result))

        actual_result = result.check()
        while not actual_result:
            actual_result = result.check()

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

        actual_result = result.check()
        while not actual_result:
            actual_result = result.check()

        self.assertEquals(actual_result, "True")
