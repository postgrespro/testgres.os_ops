from src.exceptions import ExecTimeoutException


class TestSet001_Constructor:
    def test_001__minimal(self):
        e = ExecTimeoutException("cat", 1)
        assert e.source is None
        assert e.message == "Command 'cat' timed out after 1 second(s)."
        assert e.cmd == "cat"
        assert e.timeout == 1
        assert e.output is None
        assert e.error is None
        assert str(e) == "Command 'cat' timed out after 1 second(s)."
        assert repr(e) == "ExecTimeoutException(cmd='cat', timeout=1)"
        return

    def test_002__source(self):
        e = ExecTimeoutException("cat", 1, source="aa")
        assert e.source == "aa"
        assert e.message == "Command 'cat' timed out after 1 second(s)."
        assert e.cmd == "cat"
        assert e.timeout == 1
        assert e.output is None
        assert e.error is None
        assert str(e) == "Command 'cat' timed out after 1 second(s)."
        assert repr(e) == "ExecTimeoutException(cmd='cat', timeout=1, source='aa')"
        return

    def test_003__output(self):
        e = ExecTimeoutException("cat", 1, output=b"bb")
        assert e.source is None
        assert e.message == "Command 'cat' timed out after 1 second(s)."
        assert e.cmd == "cat"
        assert e.timeout == 1
        assert e.output == b"bb"
        assert e.error is None
        assert str(e) == "Command 'cat' timed out after 1 second(s)."
        assert repr(e) == "ExecTimeoutException(cmd='cat', timeout=1, output=b'bb')"
        return

    def test_004__error(self):
        e = ExecTimeoutException("cat", 1, error=b"ee")
        assert e.source is None
        assert e.message == "Command 'cat' timed out after 1 second(s)."
        assert e.cmd == "cat"
        assert e.timeout == 1
        assert e.output is None
        assert e.error == b"ee"
        assert str(e) == "Command 'cat' timed out after 1 second(s)."
        assert repr(e) == "ExecTimeoutException(cmd='cat', timeout=1, error=b'ee')"
        return
