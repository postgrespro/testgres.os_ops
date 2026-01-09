# coding: utf-8

from testgres.common.exceptions import TestgresException
from testgres.common.exceptions import InvalidOperationException
import six
import typing


T_CMD = typing.Union[str, list]
T_OUT_DATA = typing.Union[str, bytes]
T_ERR_DATA = typing.Union[str, bytes]


class ExecUtilException(TestgresException):
    _description: typing.Optional[str]
    _command: typing.Optional[T_CMD]
    _exit_code: typing.Optional[int]
    _out: typing.Optional[T_OUT_DATA]
    _error: typing.Optional[T_ERR_DATA]

    def __init__(
        self,
        message: typing.Optional[str] = None,
        command: typing.Optional[T_CMD] = None,
        exit_code: typing.Optional[int] = None,
        out: typing.Optional[T_OUT_DATA] = None,
        error: typing.Optional[T_ERR_DATA] = None,
    ):
        assert message is None or type(message) == str  # noqa: E721
        assert command is None or type(command) in [str, list]  # noqa: E721
        assert exit_code is None or type(exit_code) == int  # noqa: E721
        assert out is None or type(out) in [str, bytes]  # noqa: E721
        assert error is None or type(error) in [str, bytes]  # noqa: E721

        super().__init__(message)

        self._description = message
        self._command = command
        self._exit_code = exit_code
        self._out = out
        self._error = error

    @property
    def message(self) -> str:
        msg = []

        if self._description:
            msg.append(self._description)

        if self._command:
            command_s = ' '.join(self._command) if isinstance(self._command, list) else self._command
            msg.append(u'Command: {}'.format(command_s))

        if self._exit_code:
            msg.append(u'Exit code: {}'.format(self._exit_code))

        if self._error:
            msg.append(u'---- Error:\n{}'.format(self._error))

        if self._out:
            msg.append(u'---- Out:\n{}'.format(self.out))

        r = self.convert_and_join(msg)
        assert type(r) == str  # noqa: E721
        return r

    @property
    def description(self) -> typing.Optional[str]:
        assert self._description is None or type(self._description) == str  # noqa: E721
        return self._description

    @property
    def command(self) -> typing.Optional[T_CMD]:
        assert self._command is None or type(self._command) in [str, list]  # noqa: E721
        return self._command

    @property
    def exit_code(self) -> typing.Optional[int]:
        assert self._exit_code is None or type(self._exit_code) == int  # noqa: E721
        return self._exit_code

    @property
    def out(self) -> typing.Optional[T_OUT_DATA]:
        assert self._out is None or type(self._out) in [str, bytes]  # noqa: E721
        return self._out

    @property
    def error(self) -> typing.Optional[T_ERR_DATA]:
        assert self._error is None or type(self._error) in [str, bytes]  # noqa: E721
        return self._error

    def __repr__(self) -> str:
        assert type(self) == ExecUtilException  # noqa: E721
        assert __class__ == ExecUtilException  # noqa: E721

        args = []

        if self._description is not None:
            args.append(("message", self._description))

        if self._command is not None:
            args.append(("command", self._command))

        if self._exit_code is not None:
            args.append(("exit_code", self._exit_code))

        if self._out is not None:
            args.append(("out", self._out))

        if self._error is not None:
            args.append(("error", self._error))

        result = "{}(".format(__class__.__name__)
        sep = ""
        for a in args:
            if a[1] is not None:
                result += sep + a[0] + "=" + repr(a[1])
                sep = ", "
            continue
        result += ")"
        return result

    @staticmethod
    def convert_and_join(msg_list):
        # Convert each byte element in the list to str
        str_list = [six.text_type(item, 'utf-8') if isinstance(item, bytes) else six.text_type(item) for item in
                    msg_list]

        # Join the list into a single string with the specified delimiter
        return six.text_type('\n').join(str_list)


__all__ = [
    type(TestgresException).__name__,
    type(InvalidOperationException).__name__,
    type(ExecUtilException).__name__,
]
