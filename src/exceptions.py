# coding: utf-8

from testgres.common.exceptions import TestgresException
from testgres.common.exceptions import InvalidOperationException
import six


class ExecUtilException(TestgresException):
    def __init__(self, message=None, command=None, exit_code=0, out=None, error=None):
        super(ExecUtilException, self).__init__(message)

        self.message = message
        self.command = command
        self.exit_code = exit_code
        self.out = out
        self.error = error

    def __str__(self):
        msg = []

        if self.message:
            msg.append(self.message)

        if self.command:
            command_s = ' '.join(self.command) if isinstance(self.command, list) else self.command
            msg.append(u'Command: {}'.format(command_s))

        if self.exit_code:
            msg.append(u'Exit code: {}'.format(self.exit_code))

        if self.error:
            msg.append(u'---- Error:\n{}'.format(self.error))

        if self.out:
            msg.append(u'---- Out:\n{}'.format(self.out))

        return self.convert_and_join(msg)

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