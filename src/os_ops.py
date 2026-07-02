from __future__ import annotations

import locale
import typing
import signal as os_signal
import subprocess


class ConnectionParams:
    def __init__(
        self,
        host: str = '127.0.0.1',
        port: typing.Optional[int] = None,
        ssh_key: typing.Optional[str] = None,
        username: typing.Optional[str] = None,
        password: typing.Optional[str] = None,
    ):
        assert type(host) is str
        assert port is None or type(port) is int
        assert ssh_key is None or type(ssh_key) is str
        assert username is None or type(username) is str
        assert password is None or type(password) is str

        self.host = host
        self.port = port
        self.ssh_key = ssh_key
        self.username = username
        self.password = password
        return


def get_default_encoding():
    if not hasattr(locale, 'getencoding'):
        locale.getencoding = locale.getpreferredencoding
    return locale.getencoding() or 'UTF-8'


class OsOperations:
    def __init__(self):
        pass

    # A property to detect a "remote" host.
    # I think, we have to remove it at all in the future.
    @property
    def remote(self) -> bool:
        raise NotImplementedError()

    @property
    def host(self) -> str:
        raise NotImplementedError()

    @property
    def port(self) -> typing.Optional[int]:
        raise NotImplementedError()

    @property
    def ssh_key(self) -> typing.Optional[str]:
        raise NotImplementedError()

    @property
    def username(self) -> typing.Optional[str]:
        raise NotImplementedError()

    def get_platform(self) -> str:
        raise NotImplementedError()

    def create_clone(self) -> OsOperations:
        raise NotImplementedError()

    # Command execution
    T_CMD = typing.Union[str, typing.List[str]]
    T_EXEC_COMMAND_RESULT = typing.Union[
        subprocess.Popen,
        str,
        bytes,
        typing.Tuple[int, str, typing.Optional[str]],
        typing.Tuple[int, bytes, typing.Optional[bytes]],
    ]

    def exec_command(
        self,
        cmd: T_CMD,
        wait_exit=False,
        verbose=False,
        expect_error=False,
        encoding: typing.Optional[str] = None,
        shell=False,
        text=False,
        input=None,
        stdin=None,
        stdout=None,
        stderr=None,
        get_process=False,
        timeout=None,
        ignore_errors=False,
        exec_env: typing.Optional[dict] = None,
        cwd: typing.Optional[str] = None
    ) -> T_EXEC_COMMAND_RESULT:
        assert type(cmd) is str or type(cmd) is list
        assert type(verbose) is bool
        assert type(expect_error) is bool
        assert encoding is None or type(encoding) is str
        assert type(wait_exit) is bool
        assert type(get_process) is bool
        assert type(ignore_errors) is bool
        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is dict
        raise NotImplementedError()

    def build_path(self, a: str, *parts: str) -> str:
        assert a is not None
        assert parts is not None
        assert type(a) is str
        assert type(parts) is tuple
        raise NotImplementedError()

    # Environment setup
    def environ(self, var_name):
        raise NotImplementedError()

    def cwd(self):
        raise NotImplementedError()

    def find_executable(self, executable):
        raise NotImplementedError()

    def is_executable(self, file):
        # Check if the file is executable
        raise NotImplementedError()

    def set_env(self, var_name, var_val):
        # Check if the directory is already in PATH
        raise NotImplementedError()

    def get_user(self):
        return self.username

    def get_name(self):
        raise NotImplementedError()

    # Work with dirs
    def makedirs(self, path, remove_existing=False):
        raise NotImplementedError()

    def makedir(self, path: str):
        assert type(path) is str
        raise NotImplementedError()

    def rmdirs(self, path, ignore_errors=True):
        raise NotImplementedError()

    def rmdir(self, path: str):
        assert type(path) is str
        raise NotImplementedError()

    def listdir(self, path):
        raise NotImplementedError()

    def path_exists(self, path):
        raise NotImplementedError()

    @property
    def pathsep(self):
        raise NotImplementedError()

    def mkdtemp(self, prefix=None):
        raise NotImplementedError()

    def mkstemp(self, prefix=None):
        raise NotImplementedError()

    def copytree(self, src, dst):
        raise NotImplementedError()

    # Work with files
    T_WRITE_DATA = typing.Union[str, bytes, typing.List[typing.Union[str, bytes]]]

    def write(
        self,
        filename: str,
        data: OsOperations.T_WRITE_DATA,
        truncate: bool = False,
        binary: bool = False,
        read_and_write: bool = False,
        encoding: typing.Optional[str] = None
    ):
        assert type(filename) is str
        assert encoding is None or type(encoding) is str
        assert data is not None
        assert type(data) in [str, bytes, list]
        assert type(truncate) is bool
        assert type(binary) is bool
        assert type(read_and_write) is bool
        assert encoding is None or type(encoding) is str

        raise NotImplementedError()

    def touch(self, filename):
        raise NotImplementedError()

    def read(
        self,
        filename: str,
        encoding: typing.Optional[str] = None,
        binary: bool = False,
    ):
        assert type(filename) is str
        assert encoding is None or type(encoding) is str
        assert type(binary) is bool
        raise NotImplementedError()

    def readlines(
        self,
        filename: str,
        num_lines: int = 0,
        binary: bool = False,
        encoding: typing.Optional[str] = None,
    ) -> typing.Union[typing.List[str], typing.List[bytes]]:
        """
        Read lines from a local file.
        If num_lines is greater than 0, only the last num_lines lines will be read.
        """
        assert type(num_lines) is int
        assert type(filename) is str
        assert type(binary) is bool
        assert encoding is None or type(encoding) is str
        assert num_lines >= 0
        raise NotImplementedError()

    def read_binary(self, filename, offset):
        assert type(filename) is str
        assert type(offset) is int
        assert offset >= 0
        raise NotImplementedError()

    def isfile(self, remote_file):
        raise NotImplementedError()

    def isdir(self, dirname):
        raise NotImplementedError()

    def get_file_size(self, filename):
        raise NotImplementedError()

    def remove_file(self, filename):
        assert type(filename) is str
        raise NotImplementedError()

    # Processes control
    def kill(self, pid: int, signal: typing.Union[int, os_signal.Signals]):
        # Kill the process
        assert type(pid) is int
        assert type(signal) is int or type(signal) is os_signal.Signals
        raise NotImplementedError()

    def get_pid(self):
        # Get current process id
        raise NotImplementedError()

    def get_process_children(self, pid: int):
        assert type(pid) is int
        raise NotImplementedError()

    def is_port_free(self, number: int):
        assert type(number) is int
        raise NotImplementedError()

    def is_port_available(self, ip: str, number: int) -> bool:
        assert type(ip) is str
        assert ip != ""
        assert type(number) is int
        assert number >= 0
        assert number <= 65535  # OK?
        raise NotImplementedError()

    def get_tempdir(self) -> str:
        raise NotImplementedError()

    def get_dirname(self, path: str) -> str:
        assert type(path) is str
        raise NotImplementedError()

    def is_abs_path(self, path: str) -> bool:
        assert type(path) is str
        raise NotImplementedError()

    def get_basename(self, path: str) -> str:
        assert type(path) is str
        raise NotImplementedError()

    def get_abs_path(self, path: str) -> str:
        assert type(path) is str
        raise NotImplementedError()
