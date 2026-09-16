from __future__ import annotations

from .types import T_OS_CMD
from .types import T_OS_SIGNAL
from .types import T_OS_TIMEOUT
from .types import T_OS_IO
from .types import T_OS_IO_ID
from .types import T_OS_RUN_INPUT
from .raise_error import RaiseError

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


class OsProcessController:
    def __enter__(self) -> OsProcessController:
        RaiseError.PropertyIsNotImplemented(__class__, "__enter__")

    def __exit__(self, exc_type, value, traceback) -> typing.Optional[bool]:
        RaiseError.PropertyIsNotImplemented(__class__, "__exit__")

    @property
    def args(self) -> T_OS_CMD:
        RaiseError.PropertyIsNotImplemented(__class__, "get_args")

    @property
    def pid(self) -> int:
        RaiseError.PropertyIsNotImplemented(__class__, "get_pid")

    @property
    def stdin(self) -> typing.Optional[T_OS_IO]:
        RaiseError.PropertyIsNotImplemented(__class__, "get_stdin")

    @property
    def stdout(self) -> typing.Optional[T_OS_IO]:
        RaiseError.PropertyIsNotImplemented(__class__, "get_stdout")

    @property
    def stderr(self) -> typing.Optional[T_OS_IO]:
        RaiseError.PropertyIsNotImplemented(__class__, "get_stderr")

    @property
    def returncode(self) -> typing.Optional[int]:
        RaiseError.PropertyIsNotImplemented(__class__, "get_returncode")

    T_COMMUNICATE_RESULT = typing.Union[
        typing.Tuple[bytes, bytes],
        typing.Tuple[str, str],
    ]

    def communicate(
        self,
        input: typing.Optional[T_OS_RUN_INPUT] = None,
        timeout: typing.Optional[T_OS_TIMEOUT] = None
    ) -> T_COMMUNICATE_RESULT:
        assert input is None or type(input) in [str, bytes]
        assert timeout is not None or type(timeout) in [int, float]
        RaiseError.MethodIsNotImplemented(__class__, "communicate")

    def send_signal(self, sig: T_OS_SIGNAL) -> None:
        assert type(sig) in [int, os_signal.Signals]
        RaiseError.MethodIsNotImplemented(__class__, "send_signal")

    def kill(self) -> None:
        RaiseError.MethodIsNotImplemented(__class__, "kill")

    def terminate(self) -> None:
        RaiseError.MethodIsNotImplemented(__class__, "terminate")

    def poll(self) -> typing.Optional[int]:
        RaiseError.MethodIsNotImplemented(__class__, "poll")

    def wait(self, timeout: typing.Optional[T_OS_TIMEOUT] = None) -> int:
        assert timeout is None or type(timeout) in [int, float]
        RaiseError.MethodIsNotImplemented(__class__, "wait")


class OsCommandResult:
    T_IO_RESULT = typing.Union[str, bytes]

    cmd: T_OS_CMD
    returncode: int
    stdout: typing.Optional[T_IO_RESULT]
    stderr: typing.Optional[T_IO_RESULT]

    def __init__(
        self,
        cmd: T_OS_CMD,
        returncode: int,
        stdout: typing.Optional[T_IO_RESULT],
        stderr: typing.Optional[T_IO_RESULT],
    ):
        assert type(cmd) in [str, list]
        assert type(returncode) is int
        assert stdout is None or type(stdout) in [str, bytes]
        assert stderr is None or type(stderr) in [str, bytes]
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        return


class OsOperations:
    def __init__(self):
        pass

    # A property to detect a "remote" host.
    # I think, we have to remove it at all in the future.
    @property
    def remote(self) -> bool:
        RaiseError.PropertyIsNotImplemented(__class__, "get_remote")

    @property
    def host(self) -> str:
        RaiseError.PropertyIsNotImplemented(__class__, "get_host")

    @property
    def port(self) -> typing.Optional[int]:
        RaiseError.PropertyIsNotImplemented(__class__, "get_port")

    @property
    def ssh_key(self) -> typing.Optional[str]:
        RaiseError.PropertyIsNotImplemented(__class__, "get_ssh_key")

    @property
    def username(self) -> typing.Optional[str]:
        RaiseError.PropertyIsNotImplemented(__class__, "get_username")

    def get_platform(self) -> str:
        RaiseError.MethodIsNotImplemented(__class__, "get_platform")

    def create_clone(self) -> OsOperations:
        RaiseError.MethodIsNotImplemented(__class__, "create_clone")

    # Command execution
    T_CMD = T_OS_CMD
    T_EXEC_COMMAND_RESULT = typing.Union[
        subprocess.Popen,
        str,
        bytes,
        typing.Tuple[int, str, typing.Optional[str]],
        typing.Tuple[int, bytes, typing.Optional[bytes]],
    ]

    def exec_command(
        self,
        cmd: T_OS_CMD,
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
        assert cwd is None or type(cwd) is str
        RaiseError.MethodIsNotImplemented(__class__, "exec_command")

    T_EXEC_ENV = typing.Dict[str, typing.Optional[str]]

    def popen(
        self,
        cmd: T_OS_CMD,
        text: typing.Optional[bool] = None,
        encoding: typing.Optional[str] = None,
        shell: bool = False,
        stdin: typing.Optional[T_OS_IO_ID] = subprocess.PIPE,
        stdout: typing.Optional[T_OS_IO_ID] = subprocess.PIPE,
        stderr: typing.Optional[T_OS_IO_ID] = subprocess.PIPE,
        exec_env: typing.Optional[T_EXEC_ENV] = None,
        cwd: typing.Optional[str] = None
    ) -> OsProcessController:
        assert type(cmd) is str or type(cmd) is list
        assert text is None or type(text) is bool
        assert encoding is None or type(encoding) is str
        assert type(shell) is bool
        assert stdin is None or type(stdin) is int or isinstance(stdin, typing.IO)
        assert stdout is None or type(stdout) is int or isinstance(stdout, typing.IO)
        assert stderr is None or type(stderr) is int or isinstance(stderr, typing.IO)
        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is str
        RaiseError.MethodIsNotImplemented(__class__, "popen")

    def run(
        self,
        cmd: T_OS_CMD,
        text: typing.Optional[bool] = None,
        encoding: typing.Optional[str] = None,
        shell: bool = False,
        input: typing.Optional[T_OS_RUN_INPUT] = None,
        stdin: typing.Optional[T_OS_IO_ID] = subprocess.PIPE,
        stdout: typing.Optional[T_OS_IO_ID] = subprocess.PIPE,
        stderr: typing.Optional[T_OS_IO_ID] = subprocess.PIPE,
        exec_env: typing.Optional[T_EXEC_ENV] = None,
        cwd: typing.Optional[str] = None,
        timeout: typing.Optional[T_OS_TIMEOUT] = None,
        check: bool = True,
    ) -> OsCommandResult:
        assert type(cmd) in [str, list]
        assert text is None or type(text) is bool
        assert encoding is None or type(encoding) is str
        assert type(shell) is bool
        assert input is None or type(input) in [str, bytes]
        assert stdin is None or type(stdin) is int or isinstance(stdin, typing.IO)
        assert stdout is None or type(stdout) is int or isinstance(stdout, typing.IO)
        assert stderr is None or type(stderr) is int or isinstance(stderr, typing.IO)
        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is str
        assert timeout is None or type(timeout) in [int, float]
        assert type(check) is bool
        RaiseError.MethodIsNotImplemented(__class__, "run")

    def build_path(self, a: str, *parts: str) -> str:
        assert a is not None
        assert parts is not None
        assert type(a) is str
        assert type(parts) is tuple
        RaiseError.MethodIsNotImplemented(__class__, "build_path")

    def quote_path(self, path: str) -> str:
        assert path is not None
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "quote_path")

    def join_command_arguments(self, cmd: typing.Iterable[str]) -> str:
        assert cmd is not None
        assert type(cmd) is list
        RaiseError.MethodIsNotImplemented(__class__, "join_command_arguments")

    # Environment setup
    def environ(self, var_name: str) -> typing.Optional[str]:
        assert type(var_name) is str
        assert var_name != ""
        RaiseError.MethodIsNotImplemented(__class__, "environ")

    def cwd(self) -> str:
        RaiseError.MethodIsNotImplemented(__class__, "cwd")

    def find_executable(self, executable: str) -> typing.Optional[str]:
        assert type(executable) is str
        assert executable != ""
        RaiseError.MethodIsNotImplemented(__class__, "find_executable")

    def is_executable(self, file: str) -> bool:
        # Check if the file is executable
        assert type(file) is str
        assert file != ""
        RaiseError.MethodIsNotImplemented(__class__, "is_executable")

    def set_env(
        self,
        var_name: str,
        var_val: typing.Optional[str],
    ) -> None:
        assert type(var_name) is str
        assert var_val is None or type(var_val) is str
        assert var_name != ""
        RaiseError.MethodIsNotImplemented(__class__, "set_env")

    def reset_env(
        self,
        var_name: str,
        default_val: typing.Optional[str],
    ) -> None:
        assert type(var_name) is str
        assert default_val is None or type(default_val) is str
        assert var_name != ""
        RaiseError.MethodIsNotImplemented(__class__, "reset_env")

    def get_user(self) -> typing.Optional[str]:
        return self.username

    def get_name(self) -> str:
        RaiseError.MethodIsNotImplemented(__class__, "get_name")

    # Work with dirs
    def makedirs(
        self,
        path: str,
        remove_existing: bool = False,
    ) -> None:
        assert type(path) is str
        assert type(remove_existing) is bool
        RaiseError.MethodIsNotImplemented(__class__, "makedirs")

    def makedir(self, path: str) -> None:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "makedir")

    T_DELAY = typing.Union[int, float]

    def rmdirs(
        self,
        path: str,
        ignore_errors: bool = True,
        attempts: int = 3,
        delay: T_DELAY = 1,
    ) -> bool:
        assert type(path) is str
        assert type(ignore_errors) is bool
        assert type(attempts) is int
        assert type(delay) is int or type(delay) is float
        assert attempts > 0
        assert delay >= 0
        RaiseError.MethodIsNotImplemented(__class__, "rmdirs")

    def rmdir(self, path: str) -> None:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "rmdir")

    def listdir(self, path: str) -> typing.List[str]:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "listdir")

    def path_exists(self, path: str) -> bool:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "path_exists")

    @property
    def pathsep(self) -> str:
        RaiseError.PropertyIsNotImplemented(__class__, "get_pathsep")

    def mkdtemp(self, prefix: typing.Optional[str] = None) -> str:
        assert prefix is None or type(prefix) is str
        RaiseError.MethodIsNotImplemented(__class__, "mkdtemp")

    def mkstemp(self, prefix: typing.Optional[str] = None) -> str:
        assert prefix is None or type(prefix) is str
        RaiseError.MethodIsNotImplemented(__class__, "mkstemp")

    def copytree(self, src: str, dst: str) -> str:
        assert type(src) is str
        assert type(dst) is str
        RaiseError.MethodIsNotImplemented(__class__, "copytree")

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
        RaiseError.MethodIsNotImplemented(__class__, "write")

    def touch(self, filename: str) -> None:
        assert type(filename) is str
        assert filename != ""
        RaiseError.MethodIsNotImplemented(__class__, "touch")

    T_READ_RESULT = typing.Union[str, bytes]

    def read(
        self,
        filename: str,
        encoding: typing.Optional[str] = None,
        binary: bool = False,
    ) -> T_READ_RESULT:
        assert type(filename) is str
        assert encoding is None or type(encoding) is str
        assert type(binary) is bool
        RaiseError.MethodIsNotImplemented(__class__, "read")

    T_READLINES_RESULT = typing.Union[typing.List[str], typing.List[bytes]]

    def readlines(
        self,
        filename: str,
        num_lines: int = 0,
        binary: bool = False,
        encoding: typing.Optional[str] = None,
    ) -> T_READLINES_RESULT:
        """
        Read lines from a local file.
        If num_lines is greater than 0, only the last num_lines lines will be read.
        """
        assert type(num_lines) is int
        assert type(filename) is str
        assert type(binary) is bool
        assert encoding is None or type(encoding) is str
        assert num_lines >= 0
        RaiseError.MethodIsNotImplemented(__class__, "readlines")

    def read_binary(
        self,
        filename: str,
        offset: int,
        size: typing.Optional[int] = None,
    ) -> bytes:
        assert type(filename) is str
        assert type(offset) is int
        assert size is None or type(size) is int
        assert offset >= 0
        assert size is None or size >= 0
        RaiseError.MethodIsNotImplemented(__class__, "read_binary")

    def isfile(self, filename: str) -> bool:
        assert type(filename) is str
        assert filename != ""
        RaiseError.MethodIsNotImplemented(__class__, "isfile")

    def isdir(self, dirname: str) -> bool:
        assert type(dirname) is str
        assert dirname != ""
        RaiseError.MethodIsNotImplemented(__class__, "isdir")

    def get_file_size(self, filename: str) -> int:
        assert type(filename) is str
        assert filename != ""
        RaiseError.MethodIsNotImplemented(__class__, "get_file_size")

    def remove_file(self, filename: str) -> None:
        assert type(filename) is str
        assert filename != ""
        RaiseError.MethodIsNotImplemented(__class__, "remove_file")

    # Processes control
    def kill(self, pid: int, signal: T_OS_SIGNAL) -> None:
        # Kill the process
        assert type(pid) is int
        assert type(signal) is int or type(signal) is os_signal.Signals
        RaiseError.MethodIsNotImplemented(__class__, "kill")

    def get_pid(self) -> int:
        # Get current process id
        RaiseError.MethodIsNotImplemented(__class__, "get_pid")

    def get_process_children(self, pid: int) -> typing.List:
        assert type(pid) is int
        RaiseError.MethodIsNotImplemented(__class__, "get_process_children")

    def is_port_free(self, number: int):
        assert type(number) is int
        RaiseError.MethodIsNotImplemented(__class__, "is_port_free")

    def get_tempdir(self) -> str:
        RaiseError.MethodIsNotImplemented(__class__, "get_tempdir")

    def get_dirname(self, path: str) -> str:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "get_dirname")

    def is_abs_path(self, path: str) -> bool:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "is_abs_path")

    def get_path_basename(self, path: str) -> str:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "get_path_basename")

    def get_abs_path(self, path: str) -> str:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "get_abs_path")

    # file size: int
    C_FILE_STAT_PROP__SIZE = "size"
    # file modification time: datetime
    C_FILE_STAT_PROP__MTIME = "mtime"

    # file properites {C_FILE_STAT_PROP__xxx -> value}
    T_FILE_STAT = typing.Dict[str, typing.Any]

    def get_file_stat(self, filename: str) -> T_FILE_STAT:
        assert type(filename) is str
        assert filename != ""
        RaiseError.MethodIsNotImplemented(__class__, "get_file_stat")

    def get_path_normpath(self, path: str) -> str:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "get_path_normpath")

    def get_path_normcase(self, path: str) -> str:
        assert type(path) is str
        RaiseError.MethodIsNotImplemented(__class__, "get_path_normcase")

    def create_file(self, filename: str) -> None:
        assert type(filename) is str
        assert filename != ""
        RaiseError.MethodIsNotImplemented(__class__, "create_file")
