import subprocess
import simplejson
import pickle
import tempfile
import shutil
from uuid import uuid4
from redis import Redis
from understudy.exceptions import NoUnderstudiesError


class Result(object):
    def __init__(self, uuid, redis):
        self.uuid = uuid
        self.redis = Redis(host=redis.host,
                           port=redis.port,
                           db=redis.db,
                           password=redis.connection.password)

    def check(self):
        result = self.redis.get("result-%s" % self.uuid)
        if result:
            self.redis.delete("result-%s" % self.uuid)

            return result

        return None

class Understudy(object):
    "Redis subscriber."
    def __init__(self, channel,
                 host='localhost', port=6379, db=0, password=None):
        self.channel = channel
        self.redis = Redis(host=host, port=port, db=db, password=password)

        self.redis.subscribe(self.channel)

    def _mkvirtualenv(self, packages):
        directory_name = tempfile.mkdtemp()
        cmd = "virtualenv %s --no-site-packages" % directory_name

        subprocess.Popen(cmd, shell=True,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=True).communicate()[0]

        if packages:
            packages = ["\"%s\"" % package for package in packages]
            cmd = "source %s/bin/activate && pip install %s" % (directory_name,
                                                                " ".join(packages))
            subprocess.Popen(cmd, shell=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             close_fds=True).communicate()[0]

        activation_file = "%s/bin/activate_this.py" % directory_name
        execfile(activation_file, dict(__file__=activation_file))

        return directory_name

    def _rmvirtualenv(self, directory):
        shutil.rmtree(directory)

    def shell(self, command):
        return subprocess.Popen(command, shell=True,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                close_fds=True).communicate()[0]


    def perform(self, serialized):
        packages = serialized['packages']

        virtualenv = self._mkvirtualenv(packages)

        kwargs = serialized['kwargs']
        args = serialized['args']
        cls = pickle.loads(serialized['cls'])
        funkt = getattr(cls, serialized['func'])

        kwargs['__understudy__'] = True
        retval = funkt(*args, **kwargs)

        self._rmvirtualenv(virtualenv)

        return retval

    def start(self):
        for message in self.redis.listen():
            if message['type'] == 'subscribe':
                continue

            message = simplejson.loads(message['data'])
            uuid = message['uuid']

            _redis = Redis(host=self.redis.host,
                           port=self.redis.port,
                           db=self.redis.db,
                           password=self.redis.connection.password)

            directive = message['directive']

            for action, args in directive.items():
                func = getattr(self, action)
                retval = func(args)

                _redis.set("result-%s" % uuid, retval)
                _redis.publish(uuid, "COMPLETE")


    def stop(self):
        self.redis.unsubscribe(self.channel)

class Lead(object):
    "Redis publisher."
    def __init__(self, channel,
                 host='localhost', port=6379, db=0, password=None):
        self.channel = channel
        self.redis = Redis(host=host, port=port, db=db, password=password)

    def _block(self, uuid):
        self.redis.subscribe(uuid)

        for message in self.redis.listen():
            if message['type'] == 'message':
                self.redis.unsubscribe(uuid)

        retval = self.redis.get("result-%s" % uuid)
        self.redis.delete("result-%s" % uuid)

        return retval

    def _handle(self, directive, block):
        understudies = self.redis.publish(self.channel,
                                          simplejson.dumps(directive))

        if not understudies:
            raise NoUnderstudiesError("No understudies found for this channel!")

        if block:
            return self._block(directive['uuid'])
        else:
            return Result(directive['uuid'], self.redis)

    def shell(self, command, block=False):
        uuid = str(uuid4())
        directive = {'uuid':uuid, 'directive':{'shell':command}}

        return self._handle(directive, block)

    def perform(self, action, block=False):
        uuid = str(uuid4())

        directive = {'uuid':uuid, 'directive':{'perform':action}}

        return self._handle(directive, block)
