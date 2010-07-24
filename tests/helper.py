TEST_DB = 15

def wait_for(result):
    _result = result.check()
    while not _result:
        _result = result.check()

    return _result


