from __future__ import annotations

import getpass
import logging
import os
import sys
import shutil
import shlex
import stat
import subprocess
import tempfile
import time
import socket

import psutil
import typing
import threading
import copy
import signal as os_signal
import datetime
import pathlib

from .exceptions import ExecUtilException
from .exceptions import InvalidOperationException
from .os_ops import ConnectionParams, OsOperations, get_default_encoding
from .raise_error import RaiseError
from .helpers import Helpers

from shutil import which as find_executable
from shutil import rmtree

CMD_TIMEOUT_SEC = 60


class LocalOperations(OsOperations):
    sm_dummy_conn_params = ConnectionParams()
    sm_single_instance: typing.Optional[OsOperations] = None
    sm_single_instance_guard = threading.Lock()

    # TODO: make it read-only
    conn_params: ConnectionParams
    _host: str
    _port: typing.Optional[int]
    _ssh_key: typing.Optional[str]
    _username: typing.Optional[str]

    def __init__(self, conn_params=None):
        super().__init__()

        if conn_params is __class__.sm_dummy_conn_params:
            return

        if conn_params is None:
            conn_params = ConnectionParams()

        self.conn_params = conn_params
        self._host = conn_params.host
        self._port = conn_params.port
        self._ssh_key = None
        self._username = conn_params.username or getpass.getuser()
        return

    @staticmethod
    def get_single_instance() -> OsOperations:
        assert __class__ == LocalOperations
        assert __class__.sm_single_instance_guard is not None

        if __class__.sm_single_instance is not None:
            assert type(__class__.sm_single_instance) is __class__
            return __class__.sm_single_instance

        with __class__.sm_single_instance_guard:
            if __class__.sm_single_instance is None:
                __class__.sm_single_instance = __class__()
        assert __class__.sm_single_instance is not None
        assert type(__class__.sm_single_instance) is __class__
        return __class__.sm_single_instance

    @property
    def remote(self) -> bool:
        return False

    @property
    def host(self) -> str:
        assert type(self._host) is str
        return self._host

    @property
    def port(self) -> typing.Optional[int]:
        assert self._port is None or type(self._port) is int
        return self._port

    @property
    def ssh_key(self) -> typing.Optional[str]:
        assert self._ssh_key is None or type(self._ssh_key) is str
        return self._ssh_key

    @property
    def username(self) -> typing.Optional[str]:
        assert self._username is None or type(self._username) is str
        return self._username

    def get_platform(self) -> str:
        return str(sys.platform)

    def create_clone(self) -> LocalOperations:
        clone = __class__(__class__.sm_dummy_conn_params)
        clone.conn_params = copy.copy(self.conn_params)
        clone._host = self._host
        clone._port = self._port
        clone._ssh_key = self._ssh_key
        clone._username = self._username
        return clone

    _T_RUN_COMMAND__RESULT = typing.Union[
        subprocess.Popen,
        typing.Tuple[int, str, typing.Optional[str]],
        typing.Tuple[int, bytes, typing.Optional[bytes]],
    ]

    def _run_command__nt(
            self,
            cmd: OsOperations.T_CMD,
            shell,
            input,
            stdin,
            stdout,
            stderr,
            get_process,
            timeout,
            encoding,
            exec_env: typing.Optional[dict],
            cwd: typing.Optional[str],
    ) -> _T_RUN_COMMAND__RESULT:
        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is str

        # TODO: why don't we use the data from input?

        extParams: typing.Dict[str, typing.Any] = dict()

        if exec_env is None:
            pass
        elif len(exec_env) == 0:
            pass
        else:
            env = os.environ.copy()
            assert type(env) is dict
            for v in exec_env.items():
                assert type(v) is tuple
                assert len(v) == 2
                assert type(v[0]) is str
                assert v[0] != ""

                if v[1] is None:
                    env.pop(v[0], None)
                else:
                    assert type(v[1]) is str
                    env[v[0]] = v[1]

            extParams["env"] = env

        with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as temp_file:
            stdout = temp_file
            stderr = subprocess.STDOUT
            process = subprocess.Popen(
                cmd,
                shell=shell,
                stdin=stdin or subprocess.PIPE if input is not None else None,
                stdout=stdout,
                stderr=stderr,
                cwd=cwd,
                text=get_process and (encoding is not None),
                encoding=encoding if get_process else None,
                **extParams,
            )
            assert isinstance(process, subprocess.Popen)
            if get_process:
                return process
            temp_file_path = temp_file.name

        # Wait process finished
        process.wait()

        # Process the output of a command from a temporary file.
        # In Windows stderr writing in stdout
        with open(temp_file_path, 'rb') as temp_file:
            output = temp_file.read()
            if encoding:
                return process.returncode, output.decode(encoding), None

            return process.returncode, output, None

    def _run_command__generic(
            self,
            cmd: OsOperations.T_CMD,
            shell,
            input,
            stdin,
            stdout,
            stderr,
            get_process,
            timeout,
            encoding,
            exec_env: typing.Optional[dict],
            cwd: typing.Optional[str],
    ) -> _T_RUN_COMMAND__RESULT:
        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is str

        input_prepared = None
        if not get_process:
            input_prepared = Helpers.prepare_process_input(input, encoding)  # throw

        assert input_prepared is None or type(input_prepared) is bytes

        extParams: typing.Dict[str, typing.Any] = dict()

        if exec_env is None:
            pass
        elif len(exec_env) == 0:
            pass
        else:
            env = os.environ.copy()
            assert type(env) is dict
            for v in exec_env.items():
                assert type(v) is tuple
                assert len(v) == 2
                assert type(v[0]) is str
                assert v[0] != ""

                if v[1] is None:
                    env.pop(v[0], None)
                else:
                    assert type(v[1]) is str
                    env[v[0]] = v[1]

            extParams["env"] = env

        process = subprocess.Popen(
            cmd,
            shell=shell,
            stdin=stdin or subprocess.PIPE if input is not None else None,
            stdout=stdout or subprocess.PIPE,
            stderr=stderr or subprocess.PIPE,
            cwd=cwd,
            text=get_process and (encoding is not None),
            encoding=encoding if get_process else None,
            **extParams
        )
        assert process is not None
        assert isinstance(process, subprocess.Popen)
        if get_process:
            return process
        try:
            output, error = process.communicate(input=input_prepared, timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            raise ExecUtilException("Command timed out after {} seconds.".format(timeout))

        assert type(output) is bytes
        assert type(error) is bytes

        if encoding:
            output = output.decode(encoding)
            error = error.decode(encoding)
        return process.returncode, output, error

    def _run_command(
            self,
            cmd: OsOperations.T_CMD,
            shell,
            input,
            stdin,
            stdout,
            stderr,
            get_process,
            timeout,
            encoding,
            exec_env: typing.Optional[dict],
            cwd: typing.Optional[str],
    ) -> _T_RUN_COMMAND__RESULT:
        """Execute a command and return the process and its output."""

        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is str

        if os.name == 'nt' and stdout is None:  # Windows
            method = __class__._run_command__nt
        else:  # Other OS
            method = __class__._run_command__generic

        return method(self, cmd, shell, input, stdin, stdout, stderr, get_process, timeout, encoding, exec_env, cwd)

    def exec_command(
        self,
        cmd: OsOperations.T_CMD,
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
    ) -> OsOperations.T_EXEC_COMMAND_RESULT:
        """
        Execute a command in a subprocess and handle the output based on the provided parameters.
        """
        assert type(expect_error) is bool
        assert type(ignore_errors) is bool
        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is str

        run_r = self._run_command(
            cmd=cmd,
            shell=shell,
            input=input,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            get_process=get_process,
            timeout=timeout,
            encoding=encoding,
            exec_env=exec_env,
            cwd=cwd,
        )

        if get_process:
            assert isinstance(run_r, subprocess.Popen)
            return run_r

        assert type(run_r) is tuple
        assert len(run_r) == 3
        assert type(run_r[0]) is int
        assert type(run_r[1]) is not None

        if expect_error:
            if run_r[0] == 0:
                raise InvalidOperationException("We expected an execution error.")
        elif ignore_errors:
            pass
        elif run_r[0] == 0:
            pass
        else:
            assert not expect_error
            assert not ignore_errors
            assert run_r[0] != 0

            RaiseError.UtilityExitedWithNonZeroCode(
                cmd=cmd,
                exit_code=run_r[0],
                msg_arg=run_r[2] or run_r[1],
                error=run_r[2],
                out=run_r[1])

        if verbose:
            return run_r

        return run_r[1]

    def build_path(self, a: str, *parts: str) -> str:
        assert a is not None
        assert parts is not None
        assert type(a) is str
        assert type(parts) is tuple
        return __class__._build_path(a, *parts)

    def quote_path(self, path: str) -> str:
        assert path is not None
        assert type(path) is str
        return __class__._quote_path(path)

    def join_command_arguments(self, cmd: typing.Iterable[str]) -> str:
        assert cmd is not None
        assert type(cmd) is list
        return __class__._join_command_arguments(cmd)

    # Environment setup
    def environ(self, var_name: str) -> typing.Optional[str]:
        assert type(var_name) is str
        assert var_name != ""
        return os.environ.get(var_name)

    def cwd(self):
        return os.getcwd()

    def find_executable(self, executable: str) -> typing.Optional[str]:
        assert type(executable) is str
        assert executable != ""
        return find_executable(executable)

    def is_executable(self, file: str) -> bool:
        # Check if the file is executable
        assert type(file) is str
        assert file != ""

        assert stat.S_IXUSR != 0
        return (os.stat(file).st_mode & stat.S_IXUSR) == stat.S_IXUSR

    def set_env(
        self,
        var_name: str,
        var_val: typing.Optional[str],
    ) -> None:
        assert type(var_name) is str
        assert var_val is None or type(var_val) is str
        assert var_name != ""

        if var_val is None:
            os.environ.pop(var_name, None)
        else:
            os.environ[var_name] = var_val
        return

    def get_name(self):
        return os.name

    # Work with dirs
    def makedirs(
        self,
        path: str,
        remove_existing: bool = False,
    ) -> None:
        assert type(path) is str
        assert type(remove_existing) is bool

        if remove_existing:
            shutil.rmtree(path, ignore_errors=True)

        os.makedirs(path, exist_ok=True)
        return

    def makedir(self, path: str) -> None:
        assert type(path) is str
        os.mkdir(path)
        return

    # [2025-02-03] Old name of parameter attempts is "retries".
    def rmdirs(
        self,
        path: str,
        ignore_errors: bool = True,
        attempts: int = 3,
        delay: OsOperations.T_DELAY = 1,
    ) -> bool:
        """
        Removes a directory and its contents, retrying on failure.
        Args:
        - path (str): The path to the directory to be removed.
        - ignore_errors (bool): If True, do not raise error if directory does not exist.
        - attempts: Number of attempts to remove the directory.
        - delay: Delay between attempts in seconds.
        """
        assert type(path) is str
        assert type(ignore_errors) is bool
        assert type(attempts) is int
        assert type(delay) is int or type(delay) is float
        assert attempts > 0
        assert delay >= 0

        a = 0
        while True:
            assert a < attempts
            a += 1
            try:
                rmtree(path)
            except FileNotFoundError:
                pass
            except Exception as e:
                if a < attempts:
                    errMsg = "Failed to remove directory {0} on attempt {1} ({2}): {3}".format(
                        path, a, type(e).__name__, e
                    )
                    logging.warning(errMsg)
                    time.sleep(delay)
                    continue

                assert a == attempts
                if not ignore_errors:
                    raise

                return False

            # OK!
            return True

    def rmdir(self, path: str) -> None:
        assert type(path) is str
        os.rmdir(path)
        return

    def listdir(self, path: str) -> typing.List[str]:
        assert type(path) is str
        return os.listdir(path)

    def path_exists(self, path: str) -> bool:
        assert type(path) is str
        return os.path.exists(path)

    @property
    def pathsep(self) -> str:
        return os.path.pathsep

    def mkdtemp(self, prefix: typing.Optional[str] = None) -> str:
        assert prefix is None or type(prefix) is str
        return tempfile.mkdtemp(prefix=prefix)

    def mkstemp(self, prefix: typing.Optional[str] = None) -> str:
        assert prefix is None or type(prefix) is str

        fd, filename = tempfile.mkstemp(prefix=prefix)
        os.close(fd)  # Close the file descriptor immediately after creating the file
        return filename

    def copytree(self, src: str, dst: str) -> str:
        assert type(src) is str
        assert type(dst) is str
        shutil.copytree(src, dst)
        return dst

    # Work with files
    def write(
        self,
        filename: str,
        data: OsOperations.T_WRITE_DATA,
        truncate: bool = False,
        binary: bool = False,
        read_and_write: bool = False,
        encoding: typing.Optional[str] = None
    ):
        """
        Write data to a file locally
        Args:
            filename: The file path where the data will be written.
            data: The data to be written to the file.
            truncate: If True, the file will be truncated before writing ('w' option);
                      if False (default), data will be appended ('a' option).
            binary: If True, the data will be written in binary mode ('b' option);
                    if False (default), the data will be written in text mode.
            read_and_write: It is ignored.
            encoding: Code page of text data.
        """
        assert type(filename) is str
        assert encoding is None or type(encoding) is str
        assert data is not None
        assert type(data) in [str, bytes, list]
        assert type(truncate) is bool
        assert type(binary) is bool
        assert type(read_and_write) is bool
        assert encoding is None or type(encoding) is str

        if not encoding:
            encoding = get_default_encoding()

        mode = "w" if truncate else "a"

        # If it is a bytes str or list
        if binary:
            mode += "b"

        assert type(mode) is str
        assert mode != ""

        with open(filename, mode, encoding=None if binary else encoding) as file:
            if isinstance(data, list):
                for s in data:
                    data2 = __class__._prepare_data_to_write(s, binary, encoding)
                    file.write(data2)
                    continue
            else:
                data2 = __class__._prepare_data_to_write(data, binary, encoding)
                file.write(data2)
        return

    @staticmethod
    def _prepare_data_to_write(
        data: typing.Union[str, bytes],
        binary: bool,
        encoding: str,
    ) -> typing.Union[str, bytes]:
        if isinstance(data, bytes):
            return data if binary else data.decode(encoding)

        if isinstance(data, str):
            return data.encode(encoding) if binary else data

        raise InvalidOperationException("Unknown type of data type [{0}].".format(type(data).__name__))

    def touch(self, filename: str) -> None:
        """
        Create a new file or update the access and modification times of an existing file.
        Args:
            filename (str): The name of the file to touch.
        """
        assert type(filename) is str
        assert filename != ""

        pathlib.Path(filename).touch(exist_ok=True)
        return

    def read(
        self,
        filename: str,
        encoding: typing.Optional[str] = None,
        binary: bool = False,
    ) -> OsOperations.T_READ_RESULT:
        assert type(filename) is str
        assert encoding is None or type(encoding) is str
        assert type(binary) is bool

        if binary:
            if encoding is not None:
                raise InvalidOperationException("Enconding is not allowed for read binary operation")

            return self._read__binary(filename)

        # python behavior
        assert (None or "abc") == "abc"
        assert ("" or "abc") == "abc"

        return self._read__text_with_encoding(filename, encoding or get_default_encoding())

    def _read__text_with_encoding(self, filename: str, encoding: str) -> str:
        assert type(filename) is str
        assert type(encoding) is str
        with open(filename, mode='r', encoding=encoding) as file:  # open in a text mode
            content = file.read()
            assert type(content) is str
            return content

    def _read__binary(self, filename: str) -> bytes:
        assert type(filename) is str
        with open(filename, 'rb') as file:  # open in a binary mode
            content = file.read()
            assert type(content) is bytes
            return content

    def readlines(
        self,
        filename: str,
        num_lines: int = 0,
        binary: bool = False,
        encoding: typing.Optional[str] = None,
    ) -> OsOperations.T_READLINES_RESULT:
        """
        Read lines from a local file.
        If num_lines is greater than 0, only the last num_lines lines will be read.
        """
        assert type(num_lines) is int
        assert type(filename) is str
        assert type(binary) is bool
        assert encoding is None or type(encoding) is str
        assert num_lines >= 0

        if binary:
            assert encoding is None
            pass
        elif encoding is None:
            encoding = get_default_encoding()
            assert type(encoding) is str
        else:
            assert type(encoding) is str
            pass

        mode = 'rb' if binary else 'r'
        if num_lines == 0:
            with open(filename, mode, encoding=encoding) as file:  # open in binary mode
                return file.readlines()
        else:
            bufsize = 8192
            buffers = 1

            with open(filename, mode, encoding=encoding) as file:  # open in binary mode
                file.seek(0, os.SEEK_END)
                end_pos = file.tell()

                while True:
                    offset = max(0, end_pos - bufsize * buffers)
                    file.seek(offset, os.SEEK_SET)
                    pos = file.tell()
                    lines = file.readlines()
                    cur_lines = len(lines)

                    if cur_lines >= num_lines or pos == 0:
                        return lines[-num_lines:]  # get last num_lines from lines

                    buffers = int(
                        buffers * max(2, int(num_lines / max(cur_lines, 1)))
                    )  # Adjust buffer size
        return

    def read_binary(self, filename: str, offset: int) -> bytes:
        assert type(filename) is str
        assert type(offset) is int

        if offset < 0:
            raise ValueError("Negative 'offset' is not supported.")

        with open(filename, 'rb') as file:  # open in a binary mode
            file.seek(offset, os.SEEK_SET)
            r = file.read()
            assert type(r) is bytes
            return r

    def isfile(self, filename: str) -> bool:
        assert type(filename) is str
        assert filename != ""
        return os.path.isfile(filename)

    def isdir(self, dirname: str) -> bool:
        assert type(dirname) is str
        assert dirname != ""
        return os.path.isdir(dirname)

    def get_file_size(self, filename: str) -> int:
        assert filename is not None
        assert type(filename) is str
        assert filename != ""
        return os.path.getsize(filename)

    def remove_file(self, filename: str) -> None:
        assert filename is not None
        assert type(filename) is str
        os.remove(filename)
        return

    # Processes control
    def kill(self, pid: int, signal: typing.Union[int, os_signal.Signals]) -> None:
        # Kill the process
        assert type(pid) is int
        assert type(signal) is int or type(signal) is os_signal.Signals
        os.kill(pid, signal)
        return

    def get_pid(self) -> int:
        # Get current process id
        return os.getpid()

    def get_process_children(self, pid: int) -> typing.List:
        assert type(pid) is int
        return psutil.Process(pid).children()

    def is_port_free(self, number: int) -> bool:
        assert type(number) is int
        assert number >= 0
        assert number <= 65535  # OK?

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", number))
                return True
            except OSError:
                return False

    def get_tempdir(self) -> str:
        r = tempfile.gettempdir()
        assert r is not None
        assert type(r) is str
        assert os.path.exists(r)
        return r

    def get_dirname(self, path: str) -> str:
        assert type(path) is str
        return os.path.dirname(path)

    def is_abs_path(self, path: str) -> bool:
        assert type(path) is str
        return os.path.isabs(path)

    def get_path_basename(self, path: str) -> str:
        assert type(path) is str
        return os.path.basename(path)

    def get_abs_path(self, path: str) -> str:
        assert type(path) is str

        normalized = os.path.normpath(path)
        assert type(normalized) is str

        # We expand the tilde locally so that the behavior matches the server
        expanded = os.path.expanduser(normalized)
        assert type(expanded) is str

        r = os.path.abspath(expanded)
        assert type(r) is str
        return r

    def get_file_stat(self, filename: str) -> OsOperations.T_FILE_STAT:
        assert type(filename) is str
        assert filename != ""

        # os.stat will automatically throw FileNotFoundError if the file does not exist
        st = os.stat(filename)

        file_stat = dict()

        file_stat[OsOperations.C_FILE_STAT_PROP__SIZE] = int(st.st_size)
        file_stat[OsOperations.C_FILE_STAT_PROP__MTIME] = datetime.datetime.fromtimestamp(
            st.st_mtime,
            tz=datetime.timezone.utc,
        )
        return file_stat

    def get_path_normpath(self, path: str) -> str:
        assert type(path) is str
        return os.path.normpath(path)

    def get_path_normcase(self, path: str) -> str:
        assert type(path) is str
        return os.path.normcase(path)

    def create_file(self, filename: str) -> None:
        assert type(filename) is str
        assert filename != ""

        # The 'xb' mode will throw a FileExistsError if the file already exists in the system
        with open(filename, "xb") as _:
            pass

        return

    @staticmethod
    def _build_path(a: str, *parts: str) -> str:
        assert a is not None
        assert parts is not None
        assert type(a) is str
        assert type(parts) is tuple
        return os.path.join(a, *parts)

    @staticmethod
    def _quote_path(path: str) -> str:
        assert type(path) is str

        if path.startswith("~"):
            # Split the path by the first slash into two parts
            # Example 1: "~root/abc/def ' \"" -> tilde_part="~root", tail_part="abc/def ' \""
            # Example 2: "~" -> tilde_part="~", tail_part=""
            parts = path.split("/", 1)
            tilde_part = parts[0]
            tail_part = parts[1] if len(parts) > 1 else ""

            if tail_part:
                # Quote ONLY the tail, protecting spaces and quotes inside it
                tail_q = __class__._quote_path2(tail_part)
                # Glue the naked tilde and the tucked tail together using a slash
                # You get: ~root/"abc/def ' \""
                return __class__._build_path(tilde_part, tail_q)

            # If there is no tail (just "~" or "~root"), leave it without quotes
            return tilde_part

        # If there is no tilde, quote the entire path
        return __class__._quote_path2(path)

    @staticmethod
    def _quote_path2(path: str) -> str:
        assert type(path) is str
        return shlex.quote(path)

    @staticmethod
    def _join_command_arguments(cmd: typing.Iterable[str]) -> str:
        assert type(cmd) is list
        for item in cmd:
            assert type(item) is str

        return " ".join(__class__._quote_path(arg) for arg in cmd)
