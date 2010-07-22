import pickle
from understudy import Lead


def understudy(*uargs, **ukwargs):
    def _understudy(func):
        def dispatch(cls, *args, **kwargs):
            if '__understudy__' in kwargs:
                del(kwargs['__understudy__'])
                return func(cls, *args, **kwargs)

            channel = uargs[0]
            host = ukwargs.get('host', 'localhost')
            port = ukwargs.get('port', 6379)
            db = ukwargs.get('db', 0)
            password = ukwargs.get('password', None)

            packages = ukwargs.get('packages', [])

            action = {'cls':pickle.dumps(cls),
                      'func':func.__name__,
                      'args':args,
                      'kwargs':kwargs,
                      'packages':packages}

            lead = Lead(channel, host=host, port=port, db=db, password=password)
            result = lead.perform(action)

            return result

        return dispatch

    return _understudy

