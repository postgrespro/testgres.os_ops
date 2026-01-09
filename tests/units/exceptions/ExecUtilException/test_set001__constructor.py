from src.exceptions import ExecUtilException


class TestSet001_Constructor:
    def test_001__default(self):
        e = ExecUtilException()
        assert e.source is None
        assert e.message == ""
        assert e.description is None
        assert e.command is None
        assert e.exit_code is None
        assert e.out is None
        assert e.error is None
        assert str(e) == ""
        assert repr(e) == "ExecUtilException()"
        return

    def test_002__description(self):
        e = ExecUtilException("operation description")
        assert e.source is None
        assert e.message == "operation description"
        assert e.description == "operation description"
        assert e.command is None
        assert e.exit_code is None
        assert e.out is None
        assert e.error is None
        assert str(e) == "operation description"
        assert repr(e) == "ExecUtilException(message='operation description')"
        return

    def test_003__commandList(self):
        e = ExecUtilException(command=["ls", "."])
        assert e.source is None
        assert e.message == "Command: ls ."
        assert e.description is None
        assert e.command == ["ls", "."]
        assert e.exit_code is None
        assert e.out is None
        assert e.error is None
        assert str(e) == "Command: ls ."
        assert repr(e) == "ExecUtilException(command=['ls', '.'])"
        return

    def test_004__commandStr(self):
        e = ExecUtilException(command="ls /home")
        assert e.source is None
        assert e.message == "Command: ls /home"
        assert e.description is None
        assert e.command == "ls /home"
        assert e.exit_code is None
        assert e.out is None
        assert e.error is None
        assert str(e) == "Command: ls /home"
        assert repr(e) == "ExecUtilException(command='ls /home')"
        return

    def test_005__exit_code(self):
        e = ExecUtilException(exit_code=123)
        assert e.source is None
        assert e.message == "Exit code: 123"
        assert e.description is None
        assert e.command is None
        assert e.exit_code == 123
        assert e.out is None
        assert e.error is None
        assert str(e) == "Exit code: 123"
        assert repr(e) == "ExecUtilException(exit_code=123)"
        return

    def test_006__outBytes(self):
        e = ExecUtilException(out=b'abcdefg\n123456')
        assert e.source is None
        assert e.message == "---- Out:\nb'abcdefg\\n123456'"
        assert e.description is None
        assert e.command is None
        assert e.exit_code is None
        assert e.out == b'abcdefg\n123456'
        assert e.error is None
        assert str(e) == "---- Out:\nb'abcdefg\\n123456'"
        assert repr(e) == "ExecUtilException(out=b'abcdefg\\n123456')"
        return

    def test_007__outStr(self):
        e = ExecUtilException(out='abcdefg\n123456')
        assert e.source is None
        assert e.message == "---- Out:\nabcdefg\n123456"
        assert e.description is None
        assert e.command is None
        assert e.exit_code is None
        assert e.out == 'abcdefg\n123456'
        assert e.error is None
        assert str(e) == "---- Out:\nabcdefg\n123456"
        assert repr(e) == "ExecUtilException(out='abcdefg\\n123456')"
        return

    def test_008__errorBytes(self):
        e = ExecUtilException(error=b'abcdefg\n123456')
        assert e.source is None
        assert e.message == "---- Error:\nb'abcdefg\\n123456'"
        assert e.description is None
        assert e.command is None
        assert e.exit_code is None
        assert e.out is None
        assert e.error == b'abcdefg\n123456'
        assert str(e) == "---- Error:\nb'abcdefg\\n123456'"
        assert repr(e) == "ExecUtilException(error=b'abcdefg\\n123456')"
        return

    def test_009__errorStr(self):
        e = ExecUtilException(error='abcdefg\n123456')
        assert e.source is None
        assert e.message == "---- Error:\nabcdefg\n123456"
        assert e.description is None
        assert e.command is None
        assert e.exit_code is None
        assert e.out is None
        assert e.error == 'abcdefg\n123456'
        assert str(e) == "---- Error:\nabcdefg\n123456"
        assert repr(e) == "ExecUtilException(error='abcdefg\\n123456')"
        return

    def test_010__all(self):
        e = ExecUtilException('descr', ['rm', 'me'], -1, 'out\n123456', b'error\n321')

        expected_msg = "descr\nCommand: rm me\nExit code: -1\n---- Error:\nb'error\\n321'\n---- Out:\nout\n123456"

        assert e.source is None
        assert e.message == expected_msg
        assert e.description == "descr"
        assert e.command == ['rm', 'me']
        assert e.exit_code == -1
        assert e.out == 'out\n123456'
        assert e.error == b'error\n321'
        assert str(e) == expected_msg
        assert repr(e) == "ExecUtilException(message='descr', command=['rm', 'me'], exit_code=-1, out='out\\n123456', error=b'error\\n321')"
        return
