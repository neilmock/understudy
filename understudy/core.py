import imp
import logging
import subprocess
import simplejson
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

class UnderstudyHandler(logging.Handler):
    def __init__(self, uuid, redis):
        logging.Handler.__init__(self)
        self.uuid = uuid
        self.redis = redis

    def emit(self, record):
        self.redis.publish(self.uuid, self.format(record))
        self.redis.lpush("understudy:log:%s" % self.uuid, self.format(record))

class Result(object):
    def __init__(self, uuid, redis):
        self.uuid = uuid
        self.log = ""
        self.redis = Redis(host=redis.host,
                           port=redis.port,
                           db=redis.db,
                           password=redis.connection.password)

    def check_log(self):
        log = self.redis.lpop("understudy:log:%s" % self.uuid)
        while log:
            self.log += log

            log = self.redis.lpop("understudy:log:%s" % self.uuid)

        return self.log

    def check(self):
        self.check_log()

        result = self.redis.get("understudy:result:%s" % self.uuid)
        if result:
            self.redis.delete("understudy:result:%s" % self.uuid)

            return result

        return None

class ShellHandler(object):
    "Handles shell tasks."
    def __init__(self, uuid, shell_command, logger=None):
        self.uuid = uuid
        self.shell_command = shell_command
        self.logger = logger

    def perform(self):
        return _exec(self.shell_command)

class FunctionHandler(object):
    "Handles understudy decorated functions."
    def __init__(self, uuid, serialized, logger=None):
        self.uuid = uuid
        self.serialized = serialized
        self.logger = logger
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
        source = simplejson.loads(self.serialized['source'])
        filepath = "%s/%s.py" % (self.virtualenv, self.uuid)
        f = open(filepath, "wb") ; f.write(source); f.close()

        f = open("%s/%s.py" % (self.virtualenv, self.uuid), "rb")
        mod = imp.load_source(self.uuid, filepath, f)
        f.close()

        kwargs = self.serialized['kwargs']
        args = self.serialized['args']

        cls = getattr(mod, self.serialized['cls'])
        instance = cls()
        funkt = getattr(instance, self.serialized['func'])

        kwargs['logger'] = self.logger
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

        logger = logging.getLogger(uuid)
        logger.setLevel(logging.INFO)
        log_handler = UnderstudyHandler(uuid, self.redis)
        logger.addHandler(log_handler)

        cls = Understudy.HANDLERS[handler]
        handler = cls(uuid, action, logger=logger)
        retval = handler.perform()

        self.redis.set("understudy:result:%s" % uuid, retval)
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
                action = message['data']

                if action == "COMPLETE":
                    self.redis.unsubscribe(uuid)
                else:
                    print action

        retval = self.redis.get("understudy:result:%s" % uuid)
        self.redis.delete("understudy:result:%s" % uuid)
        self.redis.delete("understudy:log:%s" % uuid)

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
