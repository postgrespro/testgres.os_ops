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
import struct
import ipaddress

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
        command = ["test", "-x", file]

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
    def makedirs(self, path, remove_existing=False):
        """
        Create a directory in the remote server.
        Args:
        - path (str): The path to the directory to be created.
        - remove_existing (bool): If True, the existing directory at the path will be removed.
        """
        if remove_existing:
            cmd = "rm -rf {} && mkdir -p {}".format(path, path)
        else:
            cmd = "mkdir -p {}".format(path)
        try:
            result = self.exec_command(cmd)
        except ExecUtilException as e:
            raise Exception("Couldn't create dir {} because of error {}".format(path, e.message))

        assert type(result) is bytes
        return result

    def makedir(self, path: str):
        assert type(path) is str
        cmd = ["mkdir", path]
        self.exec_command(cmd)

    def rmdirs(self, path, ignore_errors=True):
        """
        Remove a directory in the remote server.
        Args:
        - path (str): The path to the directory to be removed.
        - ignore_errors (bool): If True, do not raise error if directory does not exist.
        """
        assert type(path) is str
        assert type(ignore_errors) is bool

        # ENOENT = 2 - No such file or directory
        # ENOTDIR = 20 - Not a directory

        cmd1 = [
            "if", "[", "-d", path, "]", ";",
            "then", "rm", "-rf", path, ";",
            "elif", "[", "-e", path, "]", ";",
            "then", "{", "echo", "cannot remove '" + path + "': it is not a directory", ">&2", ";", "exit", "20", ";", "}", ";",
            "else", "{", "echo", "directory '" + path + "' does not exist", ">&2", ";", "exit", "2", ";", "}", ";",
            "fi"
        ]

        cmd2 = ["sh", "-c", subprocess.list2cmdline(cmd1)]

        try:
            self.exec_command(cmd2, encoding=Helpers.GetDefaultEncoding())
        except ExecUtilException as e:
            if e.exit_code == 2:  # No such file or directory
                return True

            if not ignore_errors:
                raise

            errMsg = "Failed to remove directory {0} ({1}): {2}".format(
                path, type(e).__name__, e
            )
            logging.warning(errMsg)
            return False
        return True

    def rmdir(self, path: str):
        assert type(path) is str
        cmd = ["rmdir", path]
        self.exec_command(cmd)
        return

    def listdir(self, path):
        """
        List all files and directories in a directory.
        Args:
        path (str): The path to the directory.
        """
        command = ["ls", path]
        output = self.exec_command(cmd=command, encoding=get_default_encoding())
        assert type(output) is str
        result = output.splitlines()
        assert type(result) is list
        return result

    def path_exists(self, path):
        command = ["test", "-e", path]

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
            command = ["mktemp", "-d", "-t", prefix + "XXXXXX"]
        else:
            command = ["mktemp", "-d"]

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
            command = ["mktemp", "-t", prefix + "XXXXXX"]
        else:
            command = ["mktemp"]

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
        if __class__._is_abs_path(dst):
            dst = __class__._build_path('~', dst)
        if self.isdir(dst):
            raise FileExistsError("Directory {} already exists.".format(dst))
        return self.exec_command("cp -r {} {}".format(src, dst))

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

        remote_cmd = [
            "mkdir",
            "-p",
            remote_directory,
            "&&",
            "cat",
            redirect_op,
            filename,
        ]

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
        self.exec_command("touch {}".format(filename))
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
        cmd = ["cat", filename]
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
            cmd = ["tail", "-n", str(num_lines), filename]
        else:
            cmd = ["cat", filename]

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

        cmd = ["tail", "-c", "+{}".format(offset + 1), filename]
        r = self.exec_command(cmd)
        assert type(r) is bytes
        return r

    def isfile(self, remote_file):
        cmd = "test -f {}; echo $?".format(remote_file)
        stdout = self.exec_command(cmd)
        assert type(stdout) is bytes
        result = int(stdout.strip())
        return result == 0

    def isdir(self, dirname):
        cmd = "if [ -d {} ]; then echo True; else echo False; fi".format(dirname)
        stdout = self.exec_command(cmd)
        assert type(stdout) is bytes
        return stdout.strip() == b"True"

    def get_file_size(self, filename):
        C_ERR_SRC = "RemoteOpertions::get_file_size"

        assert filename is not None
        assert type(filename) is str
        cmd = ["du", "-b", filename]

        s = self.exec_command(cmd, encoding=get_default_encoding())
        assert type(s) is str

        if len(s) == 0:
            raise Exception(
                "[BUG CHECK] Can't get size of file [{2}]. Remote operation returned an empty string. Check point [{0}][{1}].".format(
                    C_ERR_SRC,
                    "#001",
                    filename
                )
            )

        i = 0

        while i < len(s) and s[i].isdigit():
            assert s[i] >= '0'
            assert s[i] <= '9'
            i += 1

        if i == 0:
            raise Exception(
                "[BUG CHECK] Can't get size of file [{2}]. Remote operation returned a bad formatted string. Check point [{0}][{1}].".format(
                    C_ERR_SRC,
                    "#002",
                    filename
                )
            )

        if i == len(s):
            raise Exception(
                "[BUG CHECK] Can't get size of file [{2}]. Remote operation returned a bad formatted string. Check point [{0}][{1}].".format(
                    C_ERR_SRC,
                    "#003",
                    filename
                )
            )

        if not s[i].isspace():
            raise Exception(
                "[BUG CHECK] Can't get size of file [{2}]. Remote operation returned a bad formatted string. Check point [{0}][{1}].".format(
                    C_ERR_SRC,
                    "#004",
                    filename
                )
            )

        r = 0

        for i2 in range(0, i):
            ch = s[i2]
            assert ch >= '0'
            assert ch <= '9'
            # Here is needed to check overflow or that it is a human-valid result?
            r = (r * 10) + ord(ch) - ord('0')

        return r

    def remove_file(self, filename):
        cmd = "rm {}".format(filename)
        return self.exec_command(cmd)

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

    def is_port_available(self, ip: str, number: int) -> bool:
        assert type(ip) is str
        assert ip != ""
        assert type(number) is int
        assert number >= 0
        assert number <= 65535  # OK?

        try:
            addr = ipaddress.ip_address(ip)
            if addr.version == 4:
                return self._is_port_available_v4(
                    addr,
                    number,
                )
            if addr.version == 6:
                return self._is_port_available_v6(
                    addr,
                    number,
                )
        except ValueError:
            raise RuntimeError("Unknown format of IP: {!r}".format(ip))

        raise RuntimeError("Unsupported IP version: {!r}".format(ip))

    # --------------------------------------------------------------------
    def _is_port_available_v4(self, addr: ipaddress.IPv4Address, number: int) -> bool:
        assert type(addr) is ipaddress.IPv4Address
        assert type(number) is int
        assert number >= 0
        assert number <= 65535  # OK?

        ip_packed = addr.packed

        # 1. The IP address really depends on the architecture (we only flip it)
        ip_le = format(struct.unpack("I", ip_packed)[0], "08X")
        ip_be = format(struct.unpack("!I", ip_packed)[0], "08X")

        # 2. The port is ALWAYS output in Big Endian (just convert the number to HEX)
        port_hex = format(number, "04X")

        # 3. Build a command
        # Byte 0: 0x7F
        # Byte 1: 'E'
        # Byte 2: 'L'
        # Byte 3: 'F'
        # Byte 4: Bit class (01 — 32-bit, 02 — 64-bit)
        # Byte 5: Byte order (01 — Little Endian, 02 — Big Endian)
        grep_cmd_s = (
            'if od -An -t x1 -N 1 -j 5 /bin/bash | grep -q "01"; then '
            '  if grep -q -E "^\\s*[0-9]+:\\s*' + ip_le + ':' + port_hex + '\\s+" /proc/net/tcp; then echo "BUSY"; else echo "FREE"; fi; '
            'else '
            '  if grep -q -E "^\\s*[0-9]+:\\s*' + ip_be + ':' + port_hex + '\\s+" /proc/net/tcp; then echo "BUSY"; else echo "FREE"; fi; '
            'fi'
        )

        return self._run_grep(grep_cmd_s)

    # --------------------------------------------------------------------
    def _is_port_available_v6(self, addr: ipaddress.IPv6Address, number: int) -> bool:
        assert type(addr) is ipaddress.IPv6Address
        assert type(number) is int
        assert number >= 0
        assert number <= 65535  # OK?

        ip_bytes = addr.packed
        words = struct.unpack("!IIII", ip_bytes)

        # 1. The IP address really depends on the architecture (we only flip it)
        ip_le = "".join(format(struct.unpack("<I", struct.pack(">I", w))[0], "08X") for w in words)
        ip_be = "".join(format(w, "08X") for w in words)

        # 2. The port is ALWAYS output in Big Endian (just convert the number to HEX)
        port_hex = format(number, "04X")

        # 3. Bash script checks architecture: if 5th byte of /bin/bash is 1, then it is Little Endian
        grep_cmd_s = (
            'if od -An -t x1 -N 1 -j 5 /bin/bash | grep -q "01"; then '
            '  if grep -q -E "^\\s*[0-9]+:\\s*' + ip_le + ':' + port_hex + '\\s+" /proc/net/tcp6; then echo "BUSY"; else echo "FREE"; fi; '
            'else '
            '  if grep -q -E "^\\s*[0-9]+:\\s*' + ip_be + ':' + port_hex + '\\s+" /proc/net/tcp6; then echo "BUSY"; else echo "FREE"; fi; '
            'fi'
        )

        return self._run_grep(grep_cmd_s)

    # --------------------------------------------------------------------
    def _run_grep(self, grep_cmd_s: str) -> bool:
        assert type(grep_cmd_s) is str

        cmd = ["/bin/bash", "-c", grep_cmd_s]

        output = self.exec_command(
            cmd=cmd,
            encoding=get_default_encoding(),
        )

        if output == "BUSY\n":
            return False

        if output == "FREE\n":
            return True

        errMsg = "grep returned unexpected output: {!r}".format(output)
        raise RuntimeError(errMsg)

    # --------------------------------------------------------------------
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

    def get_basename(self, path: str) -> str:
        assert type(path) is str
        return __class__._get_basename(path)

    def get_abs_path(self, path: str) -> str:
        assert type(path) is str

        cleaned_path = __class__._normpath(path)
        assert type(cleaned_path) is str

        #
        # "-m" is used to ignore not exist parts of path
        #
        r = self.exec_command(
            ["realpath", "-m", cleaned_path],
            encoding=get_default_encoding(),
        )
        assert type(r) is str
        r = __class__._strip_last_eol(r)
        assert type(r) is str
        return r

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
    def _get_basename(path: str) -> str:
        assert type(path) is str
        return posixpath.basename(path)

    @staticmethod
    def _normpath(path: str) -> str:
        assert type(path) is str
        return posixpath.normpath(path)

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


def normalize_error(error):
    if isinstance(error, bytes):
        return error.decode()
    return error
