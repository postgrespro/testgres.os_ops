from .exceptions import ExecUtilException
from .helpers import Helpers


class RaiseError:
    @staticmethod
    def UtilityExitedWithNonZeroCode(cmd, exit_code, msg_arg, error, out):
        assert type(exit_code) is int

        msg_arg_s = __class__._TranslateDataIntoString(msg_arg)
        assert type(msg_arg_s) is str

        msg_arg_s = msg_arg_s.strip()
        if msg_arg_s == "":
            msg_arg_s = "#no_error_message"

        message = "Utility exited with non-zero code (" + str(exit_code) + "). Error: `" + msg_arg_s + "`"
        raise ExecUtilException(
            message=message,
            command=cmd,
            exit_code=exit_code,
            out=out,
            error=error)

    @staticmethod
    def CommandExecutionError(cmd, exit_code, message, error, out):
        assert type(exit_code) is int
        assert type(message) is str
        assert message != ""

        raise ExecUtilException(
            message=message,
            command=cmd,
            exit_code=exit_code,
            out=out,
            error=error)

    @staticmethod
    def _TranslateDataIntoString(data):
        if data is None:
            return ""

        if type(data) == bytes:  # noqa: E721
            return __class__._TranslateDataIntoString__FromBinary(data)

        return str(data)

    @staticmethod
    def _TranslateDataIntoString__FromBinary(data):
        assert type(data) is bytes

        try:
            return data.decode(Helpers.GetDefaultEncoding())
        except UnicodeDecodeError:
            pass

        return "#cannot_decode_text"
