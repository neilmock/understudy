import subprocess
import simplejson
import pickle
import tempfile
import shutil
from uuid import uuid4
from redis import Redis
from understudy.exceptions import NoUnderstudiesError


def _exec(cmd):
    return subprocess.Popen(cmd, shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            close_fds=True).communicate()[0]

class Result(object):
    def __init__(self, uuid, redis):
        self.uuid = uuid
        self.redis = Redis(host=redis.host,
                           port=redis.port,
                           db=redis.db,
                           password=redis.connection.password)

    def check(self):
        result = self.redis.get("result:%s" % self.uuid)
        if result:
            self.redis.delete("result:%s" % self.uuid)

            return result

        return None

class ShellHandler(object):
    "Handles shell tasks."
    def __init__(self, uuid, shell_command):
        self.uuid = uuid
        self.shell_command = shell_command

    def perform(self):
        return _exec(self.shell_command)

class FunctionHandler(object):
    "Handles understudy decorated functions."
    def __init__(self, uuid, serialized):
        self.uuid = uuid
        self.serialized = serialized
        self.virtualenv = self.mkvirtualenv()

    def mkvirtualenv(self):
        directory_name = tempfile.mkdtemp()
        cmd = "virtualenv %s --no-site-packages" % directory_name

        _exec(cmd)

        packages = self.serialized.get('packages', [])
        if packages:
            packages = ["\"%s\"" % package for package in packages]
            cmd = "source %s/bin/activate && pip install %s" % \
                (directory_name, " ".join(packages))

            _exec(cmd)

        activation_file = "%s/bin/activate_this.py" % directory_name
        execfile(activation_file, dict(__file__=activation_file))

        return directory_name

    def rmvirtualenv(self):
        shutil.rmtree(self.virtualenv)
        self.virtualenv = None

    def perform(self):
        kwargs = self.serialized['kwargs']
        args = self.serialized['args']
        cls = pickle.loads(self.serialized['cls'])
        funkt = getattr(cls, self.serialized['func'])

        kwargs['__understudy__'] = True
        retval = funkt(*args, **kwargs)

        self.rmvirtualenv()

        return retval

class Understudy(object):
    "Redis subscriber/queue processor."

    HANDLERS = {'shell':ShellHandler,
                'function':FunctionHandler,}

    def __init__(self, channel, queue=False,
                 host='localhost', port=6379, db=0, password=None):
        self.channel = channel
        self.queue = queue
        self.redis = Redis(host=host,
                           port=port,
                           db=db,
                           password=password)

        self.subscriber = Redis(host=host,
                                port=port,
                                db=db,
                                password=password)

        self.subscriber.subscribe(self.channel)

    def process_queue(self):
        msg = self.redis.lpop(self.channel)

        while msg:
            message = simplejson.loads(msg)
            self.process_message(message)

            msg = self.redis.lpop(self.channel)

    def process_message(self, message):
        uuid = message['uuid']
        handler = message['handler']
        action = message['action']

        cls = Understudy.HANDLERS[handler]
        handler = cls(uuid, action)
        retval = handler.perform()

        self.redis.set("result:%s" % uuid, retval)
        self.redis.publish(uuid, "COMPLETE")

    def start(self):
        if self.queue:
            self.process_queue()

        for message in self.subscriber.listen():
            if message['type'] == 'subscribe':
                continue

            if self.queue:
                self.process_queue()
                continue

            message = simplejson.loads(message['data'])

            self.process_message(message)

    def stop(self):
        self.subscriber.unsubscribe(self.channel)

class Lead(object):
    "Redis publisher."
    def __init__(self, channel, queue=False,
                 host='localhost', port=6379, db=0, password=None):
        self.channel = channel
        self.queue = queue
        self.redis = Redis(host=host, port=port, db=db, password=password)

    def _block(self, uuid):
        self.redis.subscribe(uuid)

        for message in self.redis.listen():
            if message['type'] == 'message':
                self.redis.unsubscribe(uuid)

        retval = self.redis.get("result:%s" % uuid)
        self.redis.delete("result:%s" % uuid)

        return retval

    def _handle(self, directive, block):
        serialized = simplejson.dumps(directive)

        if self.queue:
            self.redis.rpush(self.channel, serialized)
            self.redis.publish(self.channel, "GO!")
        else:
            understudies = self.redis.publish(self.channel, serialized)

            if not understudies:
                raise NoUnderstudiesError

        if block:
            return self._block(directive['uuid'])
        else:
            return Result(directive['uuid'], self.redis)

    def shell(self, command, block=False):
        uuid = str(uuid4())
        directive = {'uuid':uuid, 'handler':'shell', 'action':command}

        return self._handle(directive, block)

    def perform(self, action, block=False):
        uuid = str(uuid4())

        directive = {'uuid':uuid, 'handler':'function', 'action':action}

        return self._handle(directive, block)
