import inspect
import simplejson
from understudy import Lead


def understudy(*uargs, **ukwargs):
    def _understudy(func):
        def dispatch(cls, *args, **kwargs):
            if '__understudy__' in kwargs:
                del(kwargs['__understudy__'])

                logger = kwargs['logger']
                setattr(cls, 'logger', logger)
                del(kwargs['logger'])

                return func(cls, *args, **kwargs)

            channel = uargs[0]
            block = ukwargs.get('block', False)
            queue = ukwargs.get('queue', False)
            host = ukwargs.get('host', 'localhost')
            port = ukwargs.get('port', 6379)
            db = ukwargs.get('db', 0)
            password = ukwargs.get('password', None)

            packages = ukwargs.get('packages', [])

            sourcefile = inspect.getsourcefile(cls.__class__)
            f = open(sourcefile, 'rb'); source = f.read(); f.close()

            action = {'source':simplejson.dumps(source),
                      'cls':cls.__class__.__name__,
                      'func':func.__name__,
                      'args':args,
                      'kwargs':kwargs,
                      'packages':packages}

            lead = Lead(channel, queue=queue,
                        host=host, port=port, db=db, password=password)
            result = lead.perform(action, block=block)

            return result

        return dispatch

    return _understudy

