import re
import unittest
import simplejson
from multiprocessing import Process
from redis import Redis
from understudy import Lead, Understudy, Result
from understudy.exceptions import NoUnderstudiesError

from helper import TEST_DB


UUID = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'

def start_understudy(channel):
    understudy = Understudy(channel, db=TEST_DB)
    understudy.start()

class TestLead(unittest.TestCase):
    def setUp(self):
        self.lead = Lead("test", db=TEST_DB)

        # fork the understudy
        self.p = Process(target=start_understudy, args=("test",))
        self.p.start()

    def tearDown(self):
        self.p.terminate()

    def test_shell(self):
        # non-blocking
        while True:
            try:
                result = self.lead.shell("echo \"test\"")
                break
            except NoUnderstudiesError:
                pass

        self.assertTrue(isinstance(result, Result))
        self.assertTrue(re.match(UUID, result.uuid))

        actual_result = result.check()
        while not actual_result:
            actual_result = result.check()

        self.assertEquals("test\n", actual_result)

        # blocking
        result = self.lead.shell("echo \"test\"", block=True)
        self.assertEquals("test\n", result)
