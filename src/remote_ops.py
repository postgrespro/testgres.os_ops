from __future__ import annotations

import getpass
import os
import posixpath
import subprocess
import io
import logging
import typing
import copy
import re
import signal as os_signal
import time
import datetime
import shlex

from .exceptions import ExecUtilException
from .exceptions import InvalidOperationException
from .os_ops import OsOperations, ConnectionParams, get_default_encoding
from .raise_error import RaiseError
from .helpers import Helpers

error_markers = [b'error', b'Permission denied', b'fatal', b'No such file or directory']


class PsUtilProcessProxy:
    def __init__(self, ssh, pid):
        assert isinstance(ssh, RemoteOperations)
        assert type(pid) is int
        self.ssh = ssh
        self.pid = pid

    def kill(self):
        assert isinstance(self.ssh, RemoteOperations)
        assert type(self.pid) is int
        command = ["kill", str(self.pid)]
        self.ssh.exec_command(command, encoding=get_default_encoding())

    def cmdline(self):
        assert isinstance(self.ssh, RemoteOperations)
        assert type(self.pid) is int
        command = ["ps", "-p", str(self.pid), "-o", "cmd", "--no-headers"]
        output = self.ssh.exec_command(command, encoding=get_default_encoding())
        assert type(output) is str
        cmdline = output.strip()
        # TODO: This code work wrong if command line contains quoted values. Yes?
        return cmdline.split()


class RemoteOperations(OsOperations):
    _C_EOL = "\n"

    #
    # Target system is Linux only.
    #
    sm_dummy_conn_params = ConnectionParams()

    conn_params: ConnectionParams
    _host: str
    _port: typing.Optional[int]
    _ssh_key: typing.Optional[str]
    _username: typing.Optional[str]
    _ssh_cmd: typing.List[str]

    def __init__(self, conn_params: ConnectionParams):
        if conn_params is None:
            raise ValueError("Argument 'conn_params' is None.")

        super().__init__()

        if conn_params is __class__.sm_dummy_conn_params:
            return

        self.conn_params = conn_params
        self._host = conn_params.host
        self._port = conn_params.port
        self._ssh_key = conn_params.ssh_key
        self._username = conn_params.username or getpass.getuser()

        self._ssh_cmd = []

        if conn_params.password is not None:
            self._ssh_cmd += ["sshpass", "-p", conn_params.password]

        self._ssh_cmd += ["ssh"]

        if self._ssh_key is not None:
            assert type(self._ssh_key) is str
            self._ssh_cmd += ["-i", self._ssh_key]

        if self._port is not None:
            assert type(self._port) is int
            self._ssh_cmd += ["-p", str(self._port)]

        assert type(self._host) is str
        if conn_params.username is not None:
            assert type(conn_params.username) is str
            self._ssh_cmd += [conn_params.username + "@" + self._host]
        else:
            self._ssh_cmd += [self._host]
        return

    @property
    def remote(self) -> bool:
        return True

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
        return "linux"

    def create_clone(self) -> RemoteOperations:
        assert type(self._ssh_cmd) is list

        clone = __class__(__class__.sm_dummy_conn_params)
        clone.conn_params = copy.copy(self.conn_params)
        clone._host = self._host
        clone._port = self._port
        clone._ssh_key = self._ssh_key
        clone._ssh_cmd = copy.copy(self._ssh_cmd)
        clone._username = self._username
        return clone

    def exec_command(
        self,
        cmd: OsOperations.T_CMD,
        wait_exit=False,
        verbose=False,
        expect_error=False,
        encoding: typing.Optional[str] = None,
        shell=True,
        text=False,
        input=None,
        stdin=None,
        stdout=None,
        stderr=None,
        get_process=None,
        timeout=None,
        ignore_errors=False,
        exec_env: typing.Optional[dict] = None,
        cwd: typing.Optional[str] = None
    ) -> OsOperations.T_EXEC_COMMAND_RESULT:
        """
        Execute a command in the SSH session.
        Args:
        - cmd (str): The command to be executed.
        """
        assert type(expect_error) is bool
        assert type(ignore_errors) is bool
        assert exec_env is None or type(exec_env) is dict
        assert cwd is None or type(cwd) is str

        input_prepared = None
        if not get_process:
            input_prepared = Helpers.PrepareProcessInput(input, encoding)  # throw

        assert input_prepared is None or type(input_prepared) is bytes

        cmds = []

        #
        # [2026-07-01]
        #  This command prevents closing a child processes when main command finishes.
        #  For example, it saves postgres, that is started by pg_ctl utility.
        #
        cmds.append("trap '' HUP")

        if cwd is not None:
            assert type(cwd) is str
            cmds.append(__class__._build_cmdline(["cd", cwd]))

        cmds.append(__class__._build_cmdline(cmd, exec_env))

        assert len(cmds) >= 1

        cmdline = ";".join(cmds)
        assert type(cmdline) is str
        assert cmdline != ""

        # It works, too:
        # ssh_cmd = ["sh", "-c", cmdline]
        # ssh_cmd = ["bash", "-c", cmdline]

        assert type(self._ssh_cmd) is list
        assert len(self._ssh_cmd) > 0
        ssh_cmd = self._ssh_cmd + [cmdline]

        process = subprocess.Popen(
            ssh_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=get_process and (encoding is not None),
            encoding=encoding if get_process else None,
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
            run_r = process.returncode, output.decode(encoding), error.decode(encoding)
        else:
            run_r = process.returncode, output, error

        assert type(run_r[0]) is int
        assert type(run_r[1]) is type(run_r[2])

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
                msg_arg=error,
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

    # Environment setup
    def environ(self, var_name: str) -> str:
        """
        Get the value of an environment variable.
        Args:
        - var_name (str): The name of the environment variable.
        """
        cmd = "echo ${}".format(var_name)
        stdout = self.exec_command(cmd, encoding=get_default_encoding())
        assert type(stdout) is str
        return stdout.strip()

    def cwd(self):
        cmd = 'pwd'
        stdout = self.exec_command(cmd, encoding=get_default_encoding())
        assert type(stdout) is str
        return stdout.rstrip()

    def find_executable(self, executable):
        search_paths = self.environ("PATH")
        if not search_paths:
            return None

        search_paths = search_paths.split(self.pathsep)
        for path in search_paths:
            remote_file = __class__._build_path(path, executable)
            if self.isfile(remote_file):
                return remote_file

        return None

    def is_executable(self, file):
        # Check if the file is executable
        assert type(file) is str
        assert file != ""

        command = "test -x " + __class__._quote_path(file)

        exec_r = self.exec_command(
            cmd=command,
            encoding=get_default_encoding(),
            ignore_errors=True,
            verbose=True,
        )

        assert type(exec_r) is tuple
        assert len(exec_r) == 3

        exit_status, output, error = exec_r

        assert type(exit_status) is int
        assert type(output) is str
        assert type(error) is str

        if exit_status == 0:
            return True

        if exit_status == 1:
            return False

        errMsg = "Test operation returns an unknown result code: {0}. File name is [{1}].".format(
            exit_status,
            file,
        )

        RaiseError.CommandExecutionError(
            cmd=command,
            exit_code=exit_status,
            message=errMsg,
            error=error,
            out=output
        )

    def set_env(self, var_name: str, var_val: str):
        """
        Set the value of an environment variable.
        Args:
        - var_name (str): The name of the environment variable.
        - var_val (str): The value to be set for the environment variable.
        """
        return self.exec_command("export {}={}".format(var_name, var_val))

    def get_name(self):
        cmd = 'python3 -c "import os; print(os.name)"'
        stdout = self.exec_command(cmd, encoding=get_default_encoding())
        assert type(stdout) is str
        return stdout.strip()

    # Work with dirs
    def makedirs(
        self,
        path: str,
        remove_existing: bool = False,
    ) -> None:
        """
        Create a directory in the remote server.
        Args:
        - path (str): The path to the directory to be created.
        - remove_existing (bool): If True, the existing directory at the path will be removed.
        """
        assert type(path) is str
        assert path != ""

        path_q = __class__._quote_path(path)

        if remove_existing:
            cmd_p = [
                "rm",
                "-rf",
                path_q,
                "&&",
                "mkdir",
                "-p",
                path_q
            ]
        else:
            cmd_p = [
                "mkdir",
                "-p",
                path_q,
            ]

        cmd = " ".join(cmd_p)

        self.exec_command(
            cmd,
            encoding=get_default_encoding(),
        )
        return

    def makedir(self, path: str):
        assert type(path) is str
        cmd = "mkdir " + __class__._quote_path(path)
        self.exec_command(cmd, encoding=get_default_encoding())
        return

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

        # ENOENT = 2 - No such file or directory
        # ENOTDIR = 20 - Not a directory

        path_q = __class__._quote_path(path)

        cmd1_p = [
            "if", "[", "-d", path_q, "]", ";",
            "then", "rm", "-rf", path_q, ";",
            "elif", "[", "-e", path_q, "]", ";",
            "then", "{", "echo", "cannot remove " + path_q + ": it is not a directory", ">&2", ";", "exit", "20", ";", "}", ";",
            "else", "{", "echo", "directory " + path_q + " does not exist", ">&2", ";", "exit", "2", ";", "}", ";",
            "fi"
        ]

        cmd1 = " ".join(cmd1_p)

        cmd2 = ["sh", "-c", cmd1]

        a = 0
        while True:
            assert a < attempts
            a += 1
            try:
                self.exec_command(
                    cmd2,
                    encoding=Helpers.GetDefaultEncoding(),
                )
            except ExecUtilException as e:
                if e.exit_code == 2:  # No such file or directory
                    return True

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

    def rmdir(self, path: str):
        assert type(path) is str
        cmd = "rmdir " + __class__._quote_path(path)
        self.exec_command(cmd, encoding=get_default_encoding())
        return

    def listdir(self, path):
        """
        List all files and directories in a directory.
        Args:
        path (str): The path to the directory.
        """
        assert type(path) is str
        command = "ls " + __class__._quote_path(path)
        output = self.exec_command(cmd=command, encoding=get_default_encoding())
        assert type(output) is str
        result = output.splitlines()
        assert type(result) is list
        return result

    def path_exists(self, path):
        assert type(path) is str

        command = "test -e " + __class__._quote_path(path)

        exec_r = self.exec_command(
            cmd=command,
            encoding=get_default_encoding(),
            ignore_errors=True,
            verbose=True,
        )

        assert type(exec_r) is tuple
        assert len(exec_r) == 3

        exit_status, output, error = exec_r

        assert type(exit_status) is int
        assert type(output) is str
        assert type(error) is str

        if exit_status == 0:
            return True

        if exit_status == 1:
            return False

        errMsg = "Test operation returns an unknown result code: {0}. Path is [{1}].".format(
            exit_status,
            path)

        RaiseError.CommandExecutionError(
            cmd=command,
            exit_code=exit_status,
            message=errMsg,
            error=error,
            out=output
        )

    @property
    def pathsep(self):
        os_name = self.get_name()
        if os_name == "posix":
            pathsep = ":"
        elif os_name == "nt":
            pathsep = ";"
        else:
            raise Exception("Unsupported operating system: {}".format(os_name))
        return pathsep

    def mkdtemp(self, prefix=None):
        """
        Creates a temporary directory in the remote server.
        Args:
        - prefix (str): The prefix of the temporary directory name.
        """
        if prefix:
            command_p = [
                "mktemp",
                "-d",
                "-t",
                __class__._quote_path(prefix + "XXXXXX"),
            ]
        else:
            command_p = [
                "mktemp",
                "-d",
            ]

        command = " ".join(command_p)

        exec_r = self.exec_command(command, verbose=True, encoding=get_default_encoding(), ignore_errors=True)

        assert type(exec_r) is tuple
        assert len(exec_r) == 3

        exec_exitcode, exec_output, exec_error = exec_r

        assert type(exec_exitcode) is int
        assert type(exec_output) is str
        assert type(exec_error) is str

        if exec_exitcode != 0:
            RaiseError.CommandExecutionError(
                cmd=command,
                exit_code=exec_exitcode,
                message="Could not create temporary directory.",
                error=exec_error,
                out=exec_output)

        temp_dir = exec_output.strip()
        return temp_dir

    def mkstemp(self, prefix=None):
        """
        Creates a temporary file in the remote server.
        Args:
        - prefix (str): The prefix of the temporary directory name.
        """
        if prefix:
            command_p = [
                "mktemp",
                "-t",
                __class__._quote_path(prefix + "XXXXXX"),
            ]
        else:
            command_p = [
                "mktemp",
            ]

        command = " ".join(command_p)

        exec_r = self.exec_command(
            command,
            verbose=True,
            encoding=get_default_encoding(),
            ignore_errors=True,
        )

        assert type(exec_r) is tuple
        assert len(exec_r) == 3

        exec_exitcode, exec_output, exec_error = exec_r

        assert type(exec_exitcode) is int
        assert type(exec_output) is str
        assert type(exec_error) is str

        if exec_exitcode != 0:
            RaiseError.CommandExecutionError(
                cmd=command,
                exit_code=exec_exitcode,
                message="Could not create temporary file.",
                error=exec_error,
                out=exec_output)

        temp_file = exec_output.strip()
        return temp_file

    def copytree(self, src, dst):
        assert type(src) is str
        assert type(dst) is str

        if __class__._is_abs_path(dst):
            # WTF?
            dst = __class__._build_path('~', dst)

        if self.isdir(dst):
            raise FileExistsError("Directory {} already exists.".format(dst))

        cmd = "cp -r {} {}".format(
            __class__._quote_path(src),
            __class__._quote_path(dst),
        )
        return self.exec_command(cmd)

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

        # 1. Prepare the data for sending
        # Convert everything into a single string or bytes depending on the flags
        if isinstance(data, list):
            final_data = b""
            for s in data:
                r = __class__._single_chunk_to_bytes(s, encoding)
                assert type(r) is bytes
                final_data += r
                continue
            assert type(final_data) is bytes
        else:
            final_data = __class__._single_chunk_to_bytes(data, encoding)
            assert type(final_data) is bytes

        # 2. Choose an operator for bash: > (clear and write) or >> (append to the end)
        redirect_op = ">" if truncate else ">>"

        # Extract the path to the parent directory
        remote_directory = __class__._get_dirname(filename)

        remote_cmd_p = [
            "mkdir",
            "-p",
            __class__._quote_path(remote_directory),
            "&&",
            "cat",
            redirect_op,
            __class__._quote_path(filename),
        ]

        remote_cmd = " ".join(remote_cmd_p)

        # 4. Execute ONE network request
        # Pass final_data to the stdin parameter of the exec_command method
        assert type(final_data) is bytes
        self.exec_command(
            remote_cmd,
            input=final_data,
            # It does not touch our binary final_data (see PrepareProcessInput)
            # but allows to generate an error messages as text.
            encoding=get_default_encoding(),
            # Let it crash honestly if there are no rights or the disk is full
            ignore_errors=False,
        )
        return

    @staticmethod
    def _single_chunk_to_bytes(
        data: typing.Union[str, bytes],
        encoding: str,
    ) -> bytes:
        assert type(encoding) is str

        if isinstance(data, bytes):
            return data

        if isinstance(data, str):
            return data.encode(encoding)

        raise InvalidOperationException("Unknown type of data type [{0}].".format(type(data).__name__))

    def touch(self, filename):
        """
        Create a new file or update the access and modification times of an existing file on the remote server.

        Args:
            filename (str): The name of the file to touch.

        This method behaves as the 'touch' command in Unix. It's equivalent to calling 'touch filename' in the shell.
        """
        assert type(filename) is str
        assert filename != ""

        cmd = "touch " + __class__._quote_path(filename)

        self.exec_command(cmd, encoding=get_default_encoding())
        return

    def read(
        self,
        filename: str,
        encoding: typing.Optional[str] = None,
        binary: bool = False,
    ):
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

    def _read__text_with_encoding(self, filename, encoding):
        assert type(filename) is str
        assert type(encoding) is str
        content = self._read__binary(filename)
        assert type(content) is bytes
        buf0 = io.BytesIO(content)
        buf1 = io.TextIOWrapper(buf0, encoding=encoding)
        content_s = buf1.read()
        assert type(content_s) is str
        return content_s

    def _read__binary(self, filename):
        assert type(filename) is str
        cmd = "cat " + __class__._quote_path(filename)
        content = self.exec_command(cmd)
        assert type(content) is bytes
        return content

    def readlines(
        self,
        filename: str,
        num_lines: int = 0,
        binary: bool = False,
        encoding: typing.Optional[str] = None,
    ) -> typing.Union[typing.List[str], typing.List[bytes]]:
        assert type(num_lines) is int
        assert type(filename) is str
        assert type(binary) is bool
        assert encoding is None or type(encoding) is str

        if num_lines > 0:
            cmd_p = [
                "tail",
                "-n",
                str(num_lines),
                __class__._quote_path(filename),
            ]
        else:
            cmd_p = [
                "cat",
                __class__._quote_path(filename),
            ]

        cmd = " ".join(cmd_p)

        if binary:
            assert encoding is None
            pass
        elif encoding is None:
            encoding = get_default_encoding()
            assert type(encoding) is str
        else:
            assert type(encoding) is str
            pass

        result = self.exec_command(cmd, encoding=encoding)
        assert result is not None

        if binary:
            assert type(result) is bytes
            lines = result.splitlines(keepends=True)
        else:
            assert type(result) is str
            lines = result.splitlines(keepends=True)

        assert type(lines) is list
        return lines

    def read_binary(self, filename, offset):
        assert type(filename) is str
        assert type(offset) is int

        if offset < 0:
            raise ValueError("Negative 'offset' is not supported.")

        filename_q = __class__._quote_path(filename)
        cmd_p = ["tail", "-c", "+{}".format(offset + 1), filename_q]

        cmd = " ".join(cmd_p)

        r = self.exec_command(cmd)
        assert type(r) is bytes
        return r

    def isfile(self, filename: str) -> bool:
        assert type(filename) is str
        assert filename != ""

        filename_q = __class__._quote_path(filename)
        assert type(filename_q) is str

        cmd = "test -f {}; echo $?".format(filename_q)
        stdout = self.exec_command(cmd)
        assert type(stdout) is bytes
        result = int(stdout.strip())
        return result == 0

    def isdir(self, dirname: str) -> bool:
        assert type(dirname) is str
        assert dirname != ""

        dirname_q = __class__._quote_path(dirname)

        cmd = "if [ -d {} ]; then echo True; else echo False; fi".format(dirname_q)
        stdout = self.exec_command(cmd)
        assert type(stdout) is bytes
        return stdout.strip() == b"True"

    def get_file_size(self, filename: str) -> int:
        assert type(filename) is str
        assert filename != ""

        filename_q = __class__._quote_path(filename)
        assert type(filename_q) is str

        cmd = "stat -c %s " + filename_q

        # exec_command will throw ExecUtilException (e.g. with code 1) if the file does not exist
        res = self.exec_command(cmd, encoding=get_default_encoding())
        assert type(res) is str
        return int(res)

    def remove_file(self, filename: str) -> None:
        assert type(filename) is str
        assert filename != ""
        cmd = "rm " + __class__._quote_path(filename)
        self.exec_command(cmd, encoding=get_default_encoding())
        return

    # Processes control
    def kill(self, pid: int, signal: typing.Union[int, os_signal.Signals]):
        # Kill the process
        assert type(pid) is int
        assert type(signal) is int or type(signal) is os_signal.Signals
        assert int(signal) == signal
        cmd = "kill -{} {}".format(int(signal), pid)
        return self.exec_command(cmd, encoding=get_default_encoding())

    def get_pid(self):
        # Get current process id
        x = self.exec_command("echo $$", encoding=get_default_encoding())
        assert type(x) is str
        return int(x)

    def get_process_children(self, pid: int):
        assert type(pid) is int

        exec_r = self.exec_command(
            [
                "sh", "-c",
                "[ -d /proc/{0} ] || exit 100; pgrep -P {0}".format(pid),
            ],
            encoding=get_default_encoding(),
            verbose=True,
            ignore_errors=True,
        )

        assert type(exec_r) is tuple
        assert len(exec_r) == 3
        assert type(exec_r[0]) is int
        assert type(exec_r[1]) is str
        assert type(exec_r[2]) is str

        exit_code, stdout, stderr = exec_r

        assert type(exit_code) is int
        assert type(stdout) is str
        assert type(stderr) is str

        if exit_code == 100:
            err_msg = "Failed to get process children. Reason: No such process with PID {}.".format(
                pid
            )

            raise ExecUtilException(
                message=err_msg,
                exit_code=1,  # ERR: NOT FOUND
            )

        if exit_code == 0:
            stdout_clean = stdout.strip()
            if not stdout_clean:
                return []
            return [
                PsUtilProcessProxy(self, int(child_pid.strip()))
                for child_pid in stdout_clean.splitlines()
            ]

        if exit_code == 1:
            if not stderr.strip():
                # pgrep returns 1 when no children are found
                return []

        error_msg = stderr.strip() or "command exited with code {}".format(exit_code)  # noqa: E501

        raise ExecUtilException(
            "Failed to get process children for PID {}. Reason: {}".format(
                pid,
                error_msg,
            ),
            exit_code=exit_code,
        )

    def is_port_free(self, number: int) -> bool:
        assert type(number) is int
        assert number >= 0
        assert number <= 65535  # OK?

        port_hex = format(number, '04X')

        #   sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt ...
        #  137: 0A01A8C0:EC08 1DA2A959:01BB 01 00000000:00000000 02:00000000 00000000 ...
        C_REGEXP = r"^\s*[0-9]+:\s*[0-9a-fA-F]{8}:" + re.escape(port_hex) + r"\s+[0-9a-fA-F]{8}:[0-9a-fA-F]{4}\s+"

        # grep -q returns 0 if a listening socket on that port is found

        # Search /proc/net/tcp for any entry with this port
        # NOTE: grep requires quote string with regular expression
        # TODO: added a support for tcp/ip v6
        grep_cmd_s = "grep -q -E \"" + C_REGEXP + "\" /proc/net/tcp"

        cmd = [
            "/bin/bash",
            "-c",
            grep_cmd_s,
        ]

        exec_r = self.exec_command(
            cmd=cmd,
            encoding=get_default_encoding(),
            ignore_errors=True,
            verbose=True,
        )

        assert type(exec_r) is tuple
        assert len(exec_r) == 3

        exit_status, output, error = exec_r

        # grep exit 0 -> port is busy
        if exit_status == 0:
            return False

        # grep exit 1 -> port is free
        if exit_status == 1:
            return True

        # any other code is an unexpected error
        errMsg = f"grep returned unexpected exit code: {exit_status}"
        raise RaiseError.CommandExecutionError(
            cmd=cmd,
            exit_code=exit_status,
            message=errMsg,
            error=error,
            out=output
        )

    def get_tempdir(self) -> str:
        command = ["mktemp", "-u", "-d"]

        exec_r = self.exec_command(
            command,
            verbose=True,
            encoding=get_default_encoding(),
            ignore_errors=True,
        )

        assert type(exec_r) is tuple
        assert len(exec_r) == 3

        exec_exitcode, exec_output, exec_error = exec_r

        assert type(exec_exitcode) is int
        assert type(exec_output) is str
        assert type(exec_error) is str

        if exec_exitcode != 0:
            RaiseError.CommandExecutionError(
                cmd=command,
                exit_code=exec_exitcode,
                message="Could not detect a temporary directory.",
                error=exec_error,
                out=exec_output)

        temp_subdir = exec_output.strip()
        assert type(temp_subdir) is str
        temp_dir = __class__._get_dirname(temp_subdir)
        assert type(temp_dir) is str
        return temp_dir

    def get_dirname(self, path: str) -> str:
        assert type(path) is str
        return __class__._get_dirname(path)

    def is_abs_path(self, path: str) -> bool:
        assert type(path) is str
        return __class__._is_abs_path(path)

    def get_path_basename(self, path: str) -> str:
        assert type(path) is str
        return __class__._get_path_basename(path)

    def get_abs_path(self, path: str) -> str:
        assert type(path) is str

        cleaned_path = __class__._path_normpath(path)
        assert type(cleaned_path) is str

        path_q = __class__._quote_path(cleaned_path)

        cmd = "realpath -m " + path_q

        #
        # "-m" is used to ignore not exist parts of path
        #
        r = self.exec_command(
            cmd,
            encoding=get_default_encoding(),
        )
        assert type(r) is str
        r = __class__._strip_last_eol(r)
        assert type(r) is str
        return r

    def get_file_stat(self, filename: str) -> OsOperations.T_FILE_STAT:
        assert type(filename) is str
        assert filename != ""

        filename_q = __class__._quote_path(filename)
        assert type(filename_q) is str

        # Request the size (%s) and mtime in seconds (%Y) using a strict separator
        cmd = "stat -c '%s|%Y' " + filename_q

        # exec_command will throw ExecUtilException (e.g. with code 1) if the file does not exist
        res = self.exec_command(cmd, encoding=get_default_encoding())
        assert type(res) is str

        parts = res.strip().split("|")
        assert len(parts) == 2

        file_stat = dict()

        file_stat[OsOperations.C_FILE_STAT_PROP__SIZE] = int(parts[0])
        file_stat[OsOperations.C_FILE_STAT_PROP__MTIME] = datetime.datetime.fromtimestamp(
            float(parts[1]),
            tz=datetime.timezone.utc,
        )
        return file_stat

    def get_path_normpath(self, path: str) -> str:
        assert type(path) is str
        return __class__._path_normpath(path)

    def get_path_normcase(self, path: str) -> str:
        assert type(path) is str
        return __class__._path_normcase(path)

    @staticmethod
    def _build_cmdline(
        cmd,
        exec_env: typing.Optional[typing.Dict] = None,
    ) -> str:
        cmd_items = __class__._create_exec_env_list(exec_env)

        assert type(cmd_items) is list

        cmd_items.append(__class__._ensure_cmdline(cmd))

        cmdline = ';'.join(cmd_items)
        assert type(cmdline) is str
        return cmdline

    @staticmethod
    def _ensure_cmdline(cmd) -> str:
        if type(cmd) is str:
            return cmd
        if type(cmd) is list:
            return subprocess.list2cmdline(cmd)

        raise ValueError("Invalid 'cmd' argument type - {0}".format(type(cmd).__name__))

    @staticmethod
    def _create_exec_env_list(
        exec_env: typing.Optional[typing.Dict],
    ) -> typing.List[str]:
        env: typing.Dict[str, str] = dict()

        # ---------------------------------- SYSTEM ENV
        for envvar in os.environ.items():
            if __class__._does_put_envvar_into_exec_cmd(envvar[0]):
                env[envvar[0]] = envvar[1]

        # ---------------------------------- EXEC (LOCAL) ENV
        if exec_env is None:
            pass
        else:
            for envvar in exec_env.items():
                assert type(envvar) is tuple
                assert len(envvar) == 2
                assert type(envvar[0]) is str
                env[envvar[0]] = envvar[1]

        # ---------------------------------- FINAL BUILD
        result: typing.List[str] = list()
        for envvar in env.items():
            assert type(envvar) is tuple
            assert len(envvar) == 2
            assert type(envvar[0]) is str

            if envvar[1] is None:
                result.append("unset " + envvar[0])
            else:
                assert type(envvar[1]) is str
                qvalue = __class__._quote_envvar(envvar[1])
                assert type(qvalue) is str
                result.append("export " + envvar[0] + "=" + qvalue)
            continue

        return result

    sm_envs_for_exec_cmd = ["LANG", "LANGUAGE"]

    @staticmethod
    def _does_put_envvar_into_exec_cmd(name: str) -> bool:
        assert type(name) is str
        name = name.upper()
        if name.startswith("LC_"):
            return True
        if name in __class__.sm_envs_for_exec_cmd:
            return True
        return False

    @staticmethod
    def _quote_envvar(value: str) -> str:
        assert type(value) is str
        result = "\""
        for ch in value:
            if ch == "\"":
                result += "\\\""
            elif ch == "\\":
                result += "\\\\"
            else:
                result += ch
        result += "\""
        return result

    @staticmethod
    def _build_path(a: str, *parts: str) -> str:
        assert a is not None
        assert parts is not None
        assert type(a) is str
        assert type(parts) is tuple
        return posixpath.join(a, *parts)

    @staticmethod
    def _get_dirname(path: str) -> str:
        assert type(path) is str
        return posixpath.dirname(path)

    @staticmethod
    def _is_abs_path(path: str) -> bool:
        assert type(path) is str
        return posixpath.isabs(path)

    @staticmethod
    def _get_path_basename(path: str) -> str:
        assert type(path) is str
        return posixpath.basename(path)

    @staticmethod
    def _path_normpath(path: str) -> str:
        assert type(path) is str
        return posixpath.normpath(path)

    @staticmethod
    def _path_normcase(path: str) -> str:
        assert type(path) is str
        return posixpath.normcase(path)

    @staticmethod
    def _strip_last_eol(text: str) -> str:
        assert type(text) is str
        assert type(__class__._C_EOL) is str
        assert __class__._C_EOL == "\n"

        if not text.endswith(__class__._C_EOL):
            return text

        r = text[:-(len(__class__._C_EOL))]
        assert type(r) is str
        assert r + __class__._C_EOL == text
        return r

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


def normalize_error(error):
    if isinstance(error, bytes):
        return error.decode()
    return error
