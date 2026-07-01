# coding: utf-8
from tests.helpers.global_data import OsOpsDescr
from tests.helpers.global_data import OsOpsDescrs
from tests.helpers.global_data import OsOperations
from tests.helpers.run_conditions import RunConditions

import os
import sys

import pytest
import re
import tempfile
import logging
import socket
import threading
import typing
import uuid
import subprocess
import psutil
import time
import signal as os_signal

from src.exceptions import InvalidOperationException
from src.exceptions import ExecUtilException

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future as ThreadFuture


class TestOsOpsCommon:
    sm_os_ops_descrs: typing.List[OsOpsDescr] = [
        OsOpsDescrs.sm_local_os_ops_descr,
        OsOpsDescrs.sm_remote_os_ops_descr
    ]

    @pytest.fixture(
        params=[descr.os_ops for descr in sm_os_ops_descrs],
        ids=[descr.sign for descr in sm_os_ops_descrs]
    )
    def os_ops(self, request: pytest.FixtureRequest) -> OsOperations:
        assert isinstance(request, pytest.FixtureRequest)
        assert isinstance(request.param, OsOperations)
        return request.param

    def test_prop__remote(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        v = os_ops.remote
        assert v is not None or type(v) is bool

        if type(os_ops).__name__ == "RemoteOperations":
            assert v is True
        elif type(os_ops).__name__ == "LocalOperations":
            assert v is False
        else:
            raise RuntimeError("[BUG CHECK] Unknown os_ops type: {}.".format(
                type(os_ops).__name__,
            ))
        return

    def test_prop__host(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        v = os_ops.host
        assert v is not None or type(v) is str
        return

    def test_prop__port(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        v = os_ops.port
        assert v is None or type(v) is int
        return

    def test_prop__ssh_key(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        v = os_ops.ssh_key
        assert v is None or type(v) is str
        return

    def test_prop__username(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        v = os_ops.username
        assert v is None or type(v) is str
        return

    def test_get_platform(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        p = os_ops.get_platform()
        assert p is not None
        assert type(p) is str
        assert p == sys.platform
        return

    def test_get_platform__is_known(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        p = os_ops.get_platform()
        assert p is not None
        assert type(p) is str
        assert p in {"win32", "linux"}
        return

    def test_create_clone(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)
        clone = os_ops.create_clone()
        assert clone is not None
        assert clone is not os_ops
        assert type(clone) is type(os_ops)
        return

    def test_exec_command_success(self, os_ops: OsOperations):
        """
        Test exec_command for successful command execution.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        cmd = ["sh", "-c", "python3 --version"]

        response = os_ops.exec_command(cmd)
        assert type(response) is bytes
        assert b'Python 3.' in response
        return

    def test_exec_command_failure(self, os_ops: OsOperations):
        """
        Test exec_command for command execution failure.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        cmd = ["sh", "-c", "nonexistent_command"]

        while True:
            try:
                os_ops.exec_command(cmd)
            except ExecUtilException as e:
                assert type(e.exit_code) is int
                assert e.exit_code == 127

                assert type(e.message) is str
                assert type(e.error) is bytes

                assert e.message.startswith("Utility exited with non-zero code (127). Error:")
                assert "nonexistent_command" in e.message
                assert "not found" in e.message
                assert b"nonexistent_command" in e.error
                assert b"not found" in e.error
                break
            raise Exception("We wait an exception!")
        return

    def test_exec_command_failure__expect_error(self, os_ops: OsOperations):
        """
        Test exec_command for command execution failure.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        cmd = ["sh", "-c", "nonexistent_command"]

        exec_r = os_ops.exec_command(cmd, verbose=True, expect_error=True)
        assert type(exec_r) is tuple
        assert len(exec_r) == 3

        exit_status, result, error = exec_r
        assert type(exit_status) is int
        assert type(result) is bytes
        assert type(error) is bytes

        assert exit_status == 127
        assert result == b''
        assert b"nonexistent_command" in error
        assert b"not found" in error
        return

    def test_exec_command_with_exec_env(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        C_ENV_NAME = "TESTGRES_TEST__EXEC_ENV_20250414"

        cmd = ["sh", "-c", "echo ${}".format(C_ENV_NAME)]

        exec_env = {C_ENV_NAME: "Hello!"}

        response = os_ops.exec_command(cmd, exec_env=exec_env)
        assert response is not None
        assert type(response) is bytes
        assert response == b'Hello!\n'

        response = os_ops.exec_command(cmd)
        assert response is not None
        assert type(response) is bytes
        assert response == b'\n'
        return

    def test_exec_command_with_exec_env__2(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        C_ENV_NAME = "TESTGRES_TEST__EXEC_ENV_20250414"

        tmp_file_content = "echo ${{{}}}".format(C_ENV_NAME)

        logging.info("content is [{}]".format(tmp_file_content))

        tmp_file = os_ops.mkstemp()
        assert type(tmp_file) is str
        assert tmp_file != ""

        logging.info("file is [{}]".format(tmp_file))
        assert os_ops.path_exists(tmp_file)

        os_ops.write(tmp_file, tmp_file_content)

        cmd = ["sh", tmp_file]

        exec_env = {C_ENV_NAME: "Hello!"}

        response = os_ops.exec_command(cmd, exec_env=exec_env)
        assert response is not None
        assert type(response) is bytes
        assert response == b'Hello!\n'

        response = os_ops.exec_command(cmd)
        assert response is not None
        assert type(response) is bytes
        assert response == b'\n'

        os_ops.remove_file(tmp_file)
        assert not os_ops.path_exists(tmp_file)
        return

    def test_exec_command_with_cwd(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        cmd = ["pwd"]

        response = os_ops.exec_command(cmd, cwd="/tmp")
        assert response is not None
        assert type(response) is bytes
        assert response == b'/tmp\n'

        response = os_ops.exec_command(cmd)
        assert response is not None
        assert type(response) is bytes
        assert response != b'/tmp\n'
        return

    def test_exec_command__test_unset(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        C_ENV_NAME = "LANG"

        cmd = ["sh", "-c", "echo ${}".format(C_ENV_NAME)]

        response1 = os_ops.exec_command(cmd)
        assert response1 is not None
        assert type(response1) is bytes

        if response1 == b'\n':
            logging.warning("Environment variable {} is not defined.".format(C_ENV_NAME))
            return

        exec_env = {C_ENV_NAME: None}
        response2 = os_ops.exec_command(cmd, exec_env=exec_env)
        assert response2 is not None
        assert type(response2) is bytes
        assert response2 == b'\n'

        response3 = os_ops.exec_command(cmd)
        assert response3 is not None
        assert type(response3) is bytes
        assert response3 == response1
        return

    def test_exec_command__test_unset_dummy_var(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        C_ENV_NAME = "TESTGRES_TEST__DUMMY_VAR_20250414"

        cmd = ["sh", "-c", "echo ${}".format(C_ENV_NAME)]

        exec_env = {C_ENV_NAME: None}
        response2 = os_ops.exec_command(cmd, exec_env=exec_env)
        assert response2 is not None
        assert type(response2) is bytes
        assert response2 == b'\n'
        return

    def test_is_executable_true(self, os_ops: OsOperations):
        """
        Test is_executable for an existing executable.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        response = os_ops.is_executable("/bin/sh")

        assert response is True
        return

    def test_is_executable_false(self, os_ops: OsOperations):
        """
        Test is_executable for a non-executable.
        """
        assert isinstance(os_ops, OsOperations)

        response = os_ops.is_executable(__file__)

        assert response is False
        return

    def test_makedirs_and_rmdirs_success(self, os_ops: OsOperations):
        """
        Test makedirs and rmdirs for successful directory creation and removal.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        cmd = "pwd"
        stdout = os_ops.exec_command(cmd, encoding='utf-8')
        assert type(stdout) is str
        pwd = stdout.strip()

        path = "{}/test_dir".format(pwd)

        # Test makedirs
        os_ops.makedirs(path)
        assert os.path.exists(path)
        assert os_ops.path_exists(path)

        # Test rmdirs
        os_ops.rmdirs(path)
        assert not os.path.exists(path)
        assert not os_ops.path_exists(path)
        return

    def test_makedirs_failure(self, os_ops: OsOperations):
        """
        Test makedirs for failure.
        """
        # Try to create a directory in a read-only location
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        path = "/root/test_dir"

        # Test makedirs
        with pytest.raises(Exception):
            os_ops.makedirs(path)
        return

    def test_listdir(self, os_ops: OsOperations):
        """
        Test listdir for listing directory contents.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        path = "/etc"
        files = os_ops.listdir(path)
        assert isinstance(files, list)
        for f in files:
            assert f is not None
            assert type(f) is str
        return

    def test_path_exists_true__directory(self, os_ops: OsOperations):
        """
        Test path_exists for an existing directory.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        assert os_ops.path_exists("/etc") is True
        return

    def test_path_exists_true__file(self, os_ops: OsOperations):
        """
        Test path_exists for an existing file.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        assert os_ops.path_exists(__file__) is True
        return

    def test_path_exists_false__directory(self, os_ops: OsOperations):
        """
        Test path_exists for a non-existing directory.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        assert os_ops.path_exists("/nonexistent_path") is False
        return

    def test_path_exists_false__file(self, os_ops: OsOperations):
        """
        Test path_exists for a non-existing file.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        assert os_ops.path_exists("/etc/nonexistent_path.txt") is False
        return

    def test_mkdtemp__default(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        path = os_ops.mkdtemp()
        logging.info("Path is [{0}].".format(path))
        assert os.path.exists(path)
        os.rmdir(path)
        assert not os.path.exists(path)
        return

    def test_mkdtemp__custom(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        C_TEMPLATE = "abcdef"
        path = os_ops.mkdtemp(C_TEMPLATE)
        logging.info("Path is [{0}].".format(path))
        assert os.path.exists(path)
        assert C_TEMPLATE in os.path.basename(path)
        os.rmdir(path)
        assert not os.path.exists(path)
        return

    def test_rmdirs(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        path = os_ops.mkdtemp()
        assert os.path.exists(path)

        assert os_ops.rmdirs(path, ignore_errors=False) is True
        assert not os.path.exists(path)
        return

    def test_rmdirs__01_with_subfolder(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        # folder with subfolder
        path = os_ops.mkdtemp()
        assert os.path.exists(path)

        dir1 = os.path.join(path, "dir1")
        assert not os.path.exists(dir1)

        os_ops.makedirs(dir1)
        assert os.path.exists(dir1)

        assert os_ops.rmdirs(path, ignore_errors=False) is True
        assert not os.path.exists(path)
        assert not os.path.exists(dir1)
        return

    def test_rmdirs__02_with_file(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        # folder with file
        path = os_ops.mkdtemp()
        assert os.path.exists(path)

        file1 = os.path.join(path, "file1.txt")
        assert not os.path.exists(file1)

        os_ops.touch(file1)
        assert os.path.exists(file1)

        assert os_ops.rmdirs(path, ignore_errors=False) is True
        assert not os.path.exists(path)
        assert not os.path.exists(file1)
        return

    def test_rmdirs__03_with_subfolder_and_file(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        # folder with subfolder and file
        path = os_ops.mkdtemp()
        assert os.path.exists(path)

        dir1 = os.path.join(path, "dir1")
        assert not os.path.exists(dir1)

        os_ops.makedirs(dir1)
        assert os.path.exists(dir1)

        file1 = os.path.join(dir1, "file1.txt")
        assert not os.path.exists(file1)

        os_ops.touch(file1)
        assert os.path.exists(file1)

        assert os_ops.rmdirs(path, ignore_errors=False) is True
        assert not os.path.exists(path)
        assert not os.path.exists(dir1)
        assert not os.path.exists(file1)
        return

    def test_write_text_file(self, os_ops: OsOperations):
        """
        Test write for writing data to a text file.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        filename = os_ops.mkstemp()
        data = "Hello, world!"

        os_ops.write(filename, data, truncate=True)
        os_ops.write(filename, data)

        response = os_ops.read(filename)

        assert response == data + data

        os_ops.remove_file(filename)
        return

    def test_write_binary_file(self, os_ops: OsOperations):
        """
        Test write for writing data to a binary file.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        filename = "/tmp/test_file.bin"
        data = b"\x00\x01\x02\x03"

        os_ops.write(filename, data, binary=True, truncate=True)

        response = os_ops.read(filename, binary=True)

        assert response == data
        return

    def test_read_text_file(self, os_ops: OsOperations):
        """
        Test read for reading data from a text file.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        filename = "/etc/hosts"

        response = os_ops.read(filename)

        assert isinstance(response, str)
        return

    def test_read_binary_file(self, os_ops: OsOperations):
        """
        Test read for reading data from a binary file.
        """
        assert isinstance(os_ops, OsOperations)

        RunConditions.skip_if_windows()

        filename = "/usr/bin/python3"

        response = os_ops.read(filename, binary=True)

        assert isinstance(response, bytes)
        return

    def test_read__text(self, os_ops: OsOperations):
        """
        Test OsOperations::read for text data.
        """
        assert isinstance(os_ops, OsOperations)

        filename = __file__  # current file

        with open(filename, 'r') as file:  # open in a text mode
            response0 = file.read()

        assert type(response0) is str

        response1 = os_ops.read(filename)
        assert type(response1) is str
        assert response1 == response0

        response2 = os_ops.read(filename, encoding=None, binary=False)
        assert type(response2) is str
        assert response2 == response0

        response3 = os_ops.read(filename, encoding="")
        assert type(response3) is str
        assert response3 == response0

        response4 = os_ops.read(filename, encoding="UTF-8")
        assert type(response4) is str
        assert response4 == response0
        return

    def test_read__binary(self, os_ops: OsOperations):
        """
        Test OsOperations::read for binary data.
        """
        filename = __file__  # current file

        with open(filename, 'rb') as file:  # open in a binary mode
            response0 = file.read()

        assert type(response0) is bytes

        response1 = os_ops.read(filename, binary=True)
        assert type(response1) is bytes
        assert response1 == response0
        return

    def test_read__binary_and_encoding(self, os_ops: OsOperations):
        """
        Test OsOperations::read for binary data and encoding.
        """
        assert isinstance(os_ops, OsOperations)

        filename = __file__  # current file

        with pytest.raises(
                InvalidOperationException,
                match=re.escape("Enconding is not allowed for read binary operation")):
            os_ops.read(filename, encoding="", binary=True)
        return

    def test_read_binary__spec(self, os_ops: OsOperations):
        """
        Test OsOperations::read_binary.
        """
        assert isinstance(os_ops, OsOperations)

        filename = __file__  # currnt file

        with open(filename, 'rb') as file:  # open in a binary mode
            response0 = file.read()

        assert type(response0) is bytes

        response1 = os_ops.read_binary(filename, 0)
        assert type(response1) is bytes
        assert response1 == response0

        response2 = os_ops.read_binary(filename, 1)
        assert type(response2) is bytes
        assert len(response2) < len(response1)
        assert len(response2) + 1 == len(response1)
        assert response2 == response1[1:]

        response3 = os_ops.read_binary(filename, len(response1))
        assert type(response3) is bytes
        assert len(response3) == 0

        response4 = os_ops.read_binary(filename, len(response2))
        assert type(response4) is bytes
        assert len(response4) == 1
        assert response4[0] == response1[len(response1) - 1]

        response5 = os_ops.read_binary(filename, len(response1) + 1)
        assert type(response5) is bytes
        assert len(response5) == 0
        return

    def test_read_binary__spec__negative_offset(self, os_ops: OsOperations):
        """
        Test OsOperations::read_binary with negative offset.
        """
        assert isinstance(os_ops, OsOperations)

        with pytest.raises(
                ValueError,
                match=re.escape("Negative 'offset' is not supported.")):
            os_ops.read_binary(__file__, -1)
        return

    def test_get_file_size(self, os_ops: OsOperations):
        """
        Test OsOperations::get_file_size.
        """
        assert isinstance(os_ops, OsOperations)

        filename = __file__  # current file

        sz0 = os.path.getsize(filename)
        assert type(sz0) is int

        sz1 = os_ops.get_file_size(filename)
        assert type(sz1) is int
        assert sz1 == sz0
        return

    def test_isfile_true(self, os_ops: OsOperations):
        """
        Test isfile for an existing file.
        """
        assert isinstance(os_ops, OsOperations)

        filename = __file__

        response = os_ops.isfile(filename)

        assert response is True
        return

    def test_isfile_false__not_exist(self, os_ops: OsOperations):
        """
        Test isfile for a non-existing file.
        """
        assert isinstance(os_ops, OsOperations)

        filename = os.path.join(os.path.dirname(__file__), "nonexistent_file.txt")

        response = os_ops.isfile(filename)

        assert response is False
        return

    def test_isfile_false__directory(self, os_ops: OsOperations):
        """
        Test isfile for a firectory.
        """
        assert isinstance(os_ops, OsOperations)

        name = os.path.dirname(__file__)

        assert os_ops.isdir(name)

        response = os_ops.isfile(name)

        assert response is False
        return

    def test_isdir_true(self, os_ops: OsOperations):
        """
        Test isdir for an existing directory.
        """
        assert isinstance(os_ops, OsOperations)

        name = os.path.dirname(__file__)

        response = os_ops.isdir(name)

        assert response is True
        return

    def test_isdir_false__not_exist(self, os_ops: OsOperations):
        """
        Test isdir for a non-existing directory.
        """
        assert isinstance(os_ops, OsOperations)

        name = os.path.join(os.path.dirname(__file__), "it_is_nonexistent_directory")

        response = os_ops.isdir(name)

        assert response is False
        return

    def test_isdir_false__file(self, os_ops: OsOperations):
        """
        Test isdir for a file.
        """
        assert isinstance(os_ops, OsOperations)

        name = __file__

        assert os_ops.isfile(name)

        response = os_ops.isdir(name)

        assert response is False
        return

    def test_cwd(self, os_ops: OsOperations):
        """
        Test cwd.
        """
        assert isinstance(os_ops, OsOperations)

        v = os_ops.cwd()

        assert v is not None
        assert type(v) is str
        assert v != ""
        return

    class tagWriteData001:
        def __init__(self, sign, source, cp_rw, cp_truncate, cp_binary, cp_data, result):
            self.sign = sign
            self.source = source
            self.call_param__rw = cp_rw
            self.call_param__truncate = cp_truncate
            self.call_param__binary = cp_binary
            self.call_param__data = cp_data
            self.result = result
            return

    sm_write_data001 = [
        tagWriteData001("A001", "1234567890", False, False, False, "ABC", "1234567890ABC"),
        tagWriteData001("A002", b"1234567890", False, False, True, b"ABC", b"1234567890ABC"),

        tagWriteData001("B001", "1234567890", False, True, False, "ABC", "ABC"),
        tagWriteData001("B002", "1234567890", False, True, False, "ABC1234567890", "ABC1234567890"),
        tagWriteData001("B003", b"1234567890", False, True, True, b"ABC", b"ABC"),
        tagWriteData001("B004", b"1234567890", False, True, True, b"ABC1234567890", b"ABC1234567890"),

        tagWriteData001("C001", "1234567890", True, False, False, "ABC", "1234567890ABC"),
        tagWriteData001("C002", b"1234567890", True, False, True, b"ABC", b"1234567890ABC"),

        tagWriteData001("D001", "1234567890", True, True, False, "ABC", "ABC"),
        tagWriteData001("D002", "1234567890", True, True, False, "ABC1234567890", "ABC1234567890"),
        tagWriteData001("D003", b"1234567890", True, True, True, b"ABC", b"ABC"),
        tagWriteData001("D004", b"1234567890", True, True, True, b"ABC1234567890", b"ABC1234567890"),

        tagWriteData001("E001", "\0001234567890\000", False, False, False, "\000ABC\000", "\0001234567890\000\000ABC\000"),
        tagWriteData001("E002", b"\0001234567890\000", False, False, True, b"\000ABC\000", b"\0001234567890\000\000ABC\000"),

        tagWriteData001("F001", "a\nb\n", False, False, False, ["c", "d"], "a\nb\ncd"),
        tagWriteData001("F002", b"a\nb\n", False, False, True, [b"c", b"d"], b"a\nb\ncd"),

        tagWriteData001("G001", "a\nb\n", False, False, False, ["c\n\n", "d\n"], "a\nb\nc\n\nd\n"),
        tagWriteData001("G002", b"a\nb\n", False, False, True, [b"c\n\n", b"d\n"], b"a\nb\nc\n\nd\n"),

        tagWriteData001("H001", "a\nb\n\000", False, False, False, ["c\n\n", "d\n"], "a\nb\n\000c\n\nd\n"),
        tagWriteData001("H002", b"a\nb\n\000", False, False, True, [b"c\n\n", b"d\n"], b"a\nb\n\000c\n\nd\n"),

        tagWriteData001("J001", "a\nb\n\000", False, False, False, ["c\n\n\x00", "d\n"], "a\nb\n\000c\n\n\x00d\n"),
        tagWriteData001("J002", b"a\nb\n\000", False, False, True, [b"c\n\n\x00", b"d\n"], b"a\nb\n\000c\n\n\x00d\n"),
    ]

    @pytest.fixture(
        params=sm_write_data001,
        ids=[x.sign for x in sm_write_data001],
    )
    def write_data001(self, request):
        assert isinstance(request, pytest.FixtureRequest)
        assert type(request.param) is __class__.tagWriteData001
        return request.param

    def test_write(self, write_data001: tagWriteData001, os_ops: OsOperations):
        assert type(write_data001) is __class__.tagWriteData001
        assert isinstance(os_ops, OsOperations)

        mode = "w+b" if write_data001.call_param__binary else "w+"

        with tempfile.NamedTemporaryFile(mode=mode, delete=True) as tmp_file:
            tmp_file.write(write_data001.source)
            tmp_file.flush()

            os_ops.write(
                tmp_file.name,
                write_data001.call_param__data,
                read_and_write=write_data001.call_param__rw,
                truncate=write_data001.call_param__truncate,
                binary=write_data001.call_param__binary)

            tmp_file.seek(0)

            s = tmp_file.read()

            assert s == write_data001.result
        return

    def test_touch(self, os_ops: OsOperations):
        """
        Test touch for creating a new file or updating access and modification times of an existing file.
        """
        assert isinstance(os_ops, OsOperations)

        filename = os_ops.mkstemp()

        # TODO: this test does not check the result of 'touch' command!

        os_ops.touch(filename)

        assert os_ops.isfile(filename)

        os_ops.remove_file(filename)
        return

    def test_is_port_free__true(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        C_LIMIT = 128

        ports = set(range(1024, 65535))
        assert type(ports) is set

        ok_count = 0
        no_count = 0

        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                except OSError:
                    continue

            r = os_ops.is_port_free(port)

            if r:
                ok_count += 1
                logging.info("OK. Port {} is free.".format(port))
            else:
                no_count += 1
                logging.warning("NO. Port {} is not free.".format(port))

            if ok_count == C_LIMIT:
                return

            if no_count == C_LIMIT:
                raise RuntimeError("To many false positive test attempts.")

        if ok_count == 0:
            raise RuntimeError("No one free port was found.")
        return

    def test_is_port_free__false(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        C_LIMIT = 10

        ports = set(range(1024, 65535))
        assert type(ports) is set

        def LOCAL_server(s: socket.socket):
            assert s is not None
            assert type(s) is socket.socket

            try:
                while True:
                    r = s.accept()

                    if r is None:
                        break
            except Exception as e:
                assert e is not None
                pass

        ok_count = 0
        no_count = 0

        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                except OSError:
                    continue

                th = threading.Thread(target=LOCAL_server, args=[s])

                s.listen(10)

                assert type(th) is threading.Thread
                th.start()

                try:
                    r = os_ops.is_port_free(port)
                finally:
                    s.shutdown(2)
                    th.join()

                if not r:
                    ok_count += 1
                    logging.info("OK. Port {} is not free.".format(port))
                else:
                    no_count += 1
                    logging.warning("NO. Port {} does not accept connection.".format(port))

                if ok_count == C_LIMIT:
                    return

                if no_count == C_LIMIT:
                    raise RuntimeError("To many false positive test attempts.")

        if ok_count == 0:
            raise RuntimeError("No one free port was found.")
        return

    def test_get_tempdir(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        dir = os_ops.get_tempdir()
        assert type(dir) is str
        assert os_ops.path_exists(dir)
        assert os.path.exists(dir)

        file_path = os.path.join(dir, "testgres--" + uuid.uuid4().hex + ".tmp")

        os_ops.write(file_path, "1234", binary=False)

        assert os_ops.path_exists(file_path)
        assert os.path.exists(file_path)

        d = os_ops.read(file_path, binary=False)

        assert d == "1234"

        os_ops.remove_file(file_path)

        assert not os_ops.path_exists(file_path)
        assert not os.path.exists(file_path)
        return

    def test_get_tempdir__compare_with_py_info(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        actual_dir = os_ops.get_tempdir()
        assert actual_dir is not None
        assert type(actual_dir) is str

        # --------
        cmd = [sys.executable, "-c", "import tempfile;print(tempfile.gettempdir());"]

        expected_dir_b = os_ops.exec_command(cmd)
        assert type(expected_dir_b) is bytes
        expected_dir = expected_dir_b.decode()
        assert type(expected_dir) is str
        assert actual_dir + "\n" == expected_dir
        return

    class tagData_OS_OPS__NUMS:
        os_ops_descr: OsOpsDescr
        nums: int

        def __init__(self, os_ops_descr: OsOpsDescr, nums: int):
            assert isinstance(os_ops_descr, OsOpsDescr)
            assert type(nums) is int

            self.os_ops_descr = os_ops_descr
            self.nums = nums
            return

    sm_test_exclusive_creation__mt__data = [
        tagData_OS_OPS__NUMS(OsOpsDescrs.sm_local_os_ops_descr, 100000),
        tagData_OS_OPS__NUMS(OsOpsDescrs.sm_remote_os_ops_descr, 120),
    ]

    @pytest.fixture(
        params=sm_test_exclusive_creation__mt__data,
        ids=[x.os_ops_descr.sign for x in sm_test_exclusive_creation__mt__data]
    )
    def data001(self, request: pytest.FixtureRequest) -> tagData_OS_OPS__NUMS:
        assert isinstance(request, pytest.FixtureRequest)
        return request.param

    def test_mkdir__mt(self, data001: tagData_OS_OPS__NUMS):
        assert type(data001) is __class__.tagData_OS_OPS__NUMS

        N_WORKERS = 4
        N_NUMBERS = data001.nums
        assert type(N_NUMBERS) is int

        os_ops = data001.os_ops_descr.os_ops
        assert isinstance(os_ops, OsOperations)

        lock_dir_prefix = "test_mkdir_mt--" + uuid.uuid4().hex

        lock_dir = os_ops.mkdtemp(prefix=lock_dir_prefix)

        logging.info("A lock file [{}] is creating ...".format(lock_dir))

        assert os.path.exists(lock_dir)

        def MAKE_PATH(lock_dir: str, num: int) -> str:
            assert type(lock_dir) is str
            assert type(num) is int
            return os.path.join(lock_dir, str(num) + ".lock")

        def LOCAL_WORKER(os_ops: OsOperations,
                         workerID: int,
                         lock_dir: str,
                         cNumbers: int,
                         reservedNumbers: typing.Set[int]) -> None:
            assert isinstance(os_ops, OsOperations)
            assert type(workerID) is int
            assert type(lock_dir) is str
            assert type(cNumbers) is int
            assert type(reservedNumbers) is set
            assert cNumbers > 0
            assert len(reservedNumbers) == 0

            assert os.path.exists(lock_dir)

            def LOG_INFO(template: str, *args) -> None:
                assert type(template) is str
                assert type(args) is tuple

                msg = template.format(*args)
                assert type(msg) is str

                logging.info("[Worker #{}] {}".format(workerID, msg))
                return

            LOG_INFO("HELLO! I am here!")

            for num in range(cNumbers):
                assert num not in reservedNumbers

                file_path = MAKE_PATH(lock_dir, num)

                try:
                    os_ops.makedir(file_path)
                except Exception as e:
                    LOG_INFO(
                        "Can't reserve {}. Error ({}): {}",
                        num,
                        type(e).__name__,
                        str(e)
                    )
                    continue

                LOG_INFO("Number {} is reserved!", num)
                assert os_ops.path_exists(file_path)
                reservedNumbers.add(num)
                continue

            n_total = cNumbers
            n_ok = len(reservedNumbers)
            assert n_ok <= n_total

            LOG_INFO("Finish! OK: {}. FAILED: {}.", n_ok, n_total - n_ok)
            return

        # -----------------------
        logging.info("Worker are creating ...")

        threadPool = ThreadPoolExecutor(
            max_workers=N_WORKERS,
            thread_name_prefix="ex_creator"
        )

        class tadWorkerData:
            future: ThreadFuture
            reservedNumbers: typing.Set[int]

        workerDatas: typing.List[tadWorkerData] = list()

        nErrors = 0

        try:
            for n in range(N_WORKERS):
                logging.info("worker #{} is creating ...".format(n))

                workerDatas.append(tadWorkerData())

                workerDatas[n].reservedNumbers = set()

                workerDatas[n].future = threadPool.submit(
                    LOCAL_WORKER,
                    os_ops,
                    n,
                    lock_dir,
                    N_NUMBERS,
                    workerDatas[n].reservedNumbers
                )

                assert workerDatas[n].future is not None

            logging.info("OK. All the workers were created!")
        except Exception as e:
            nErrors += 1
            logging.error("A problem is detected ({}): {}".format(type(e).__name__, str(e)))

        logging.info("Will wait for stop of all the workers...")

        nWorkers = 0

        assert type(workerDatas) is list

        for i in range(len(workerDatas)):
            worker = workerDatas[i].future

            if worker is None:
                continue

            nWorkers += 1

            assert isinstance(worker, ThreadFuture)

            try:
                logging.info("Wait for worker #{}".format(i))
                worker.result()
            except Exception as e:
                nErrors += 1
                logging.error("Worker #{} finished with error ({}): {}".format(
                    i,
                    type(e).__name__,
                    str(e),
                ))
            continue

        assert nWorkers == N_WORKERS

        if nErrors != 0:
            raise RuntimeError("Some problems were detected. Please examine the log messages.")

        logging.info("OK. Let's check worker results!")

        reservedNumbers: typing.Dict[int, int] = dict()

        for i in range(N_WORKERS):
            logging.info("Worker #{} is checked ...".format(i))

            workerNumbers = workerDatas[i].reservedNumbers
            assert type(workerNumbers) is set

            for n in workerNumbers:
                if n < 0 or n >= N_NUMBERS:
                    nErrors += 1
                    logging.error("Unexpected number {}".format(n))
                    continue

                if n in reservedNumbers.keys():
                    nErrors += 1
                    logging.error("Number {} was already reserved by worker #{}".format(
                        n,
                        reservedNumbers[n]
                    ))
                else:
                    reservedNumbers[n] = i

                file_path = MAKE_PATH(lock_dir, n)
                if not os_ops.path_exists(file_path):
                    nErrors += 1
                    logging.error("File {} is not found!".format(file_path))
                    continue

                continue

        logging.info("OK. Let's check reservedNumbers!")

        for n in range(N_NUMBERS):
            if n not in reservedNumbers.keys():
                nErrors += 1
                logging.error("Number {} is not reserved!".format(n))
                continue

            file_path = MAKE_PATH(lock_dir, n)
            if not os_ops.path_exists(file_path):
                nErrors += 1
                logging.error("File {} is not found!".format(file_path))
                continue

            # OK!
            continue

        logging.info("Verification is finished! Total error count is {}.".format(nErrors))

        if nErrors == 0:
            logging.info("Root lock-directory [{}] will be deleted.".format(
                lock_dir
            ))

            for n in range(N_NUMBERS):
                file_path = MAKE_PATH(lock_dir, n)
                try:
                    os_ops.rmdir(file_path)
                except Exception as e:
                    nErrors += 1
                    logging.error("Cannot delete directory [{}]. Error ({}): {}".format(
                        file_path,
                        type(e).__name__,
                        str(e)
                    ))
                    continue

                if os_ops.path_exists(file_path):
                    nErrors += 1
                    logging.error("Directory {} is not deleted!".format(file_path))
                    continue

            if nErrors == 0:
                try:
                    os_ops.rmdir(lock_dir)
                except Exception as e:
                    nErrors += 1
                    logging.error("Cannot delete directory [{}]. Error ({}): {}".format(
                        lock_dir,
                        type(e).__name__,
                        str(e)
                    ))

        logging.info("Test is finished! Total error count is {}.".format(nErrors))
        return

    T_KILL_SIGNAL_DESCR = typing.Tuple[
        str,
        typing.Union[int, os_signal.Signals],
        str
    ]

    sm_kill_signal_ids: typing.List[T_KILL_SIGNAL_DESCR] = [
        ("SIGINT", os_signal.SIGINT, "2"),
        # ("SIGQUIT", os_signal.SIGQUIT, "3"), # it creates coredump
        ("SIGKILL", os_signal.SIGKILL, "9"),
        ("SIGTERM", os_signal.SIGTERM, "15"),
        ("2", 2, "2"),
        # ("3", 3, "3"), # it creates coredump
        ("9", 9, "9"),
        ("15", 15, "15"),
    ]

    @pytest.fixture(
        params=sm_kill_signal_ids,
        ids=["signal: {}".format(x[0]) for x in sm_kill_signal_ids],
    )
    def kill_signal_id(self, request: pytest.FixtureRequest) -> T_KILL_SIGNAL_DESCR:
        assert isinstance(request, pytest.FixtureRequest)
        assert type(request.param) is tuple
        return request.param

    def test_kill_signal(
        self,
        kill_signal_id: T_KILL_SIGNAL_DESCR,
    ):
        assert type(kill_signal_id) is tuple
        assert "{}".format(kill_signal_id[1]) == kill_signal_id[2]
        assert "{}".format(int(kill_signal_id[1])) == kill_signal_id[2]
        return

    def test_kill(
        self,
        os_ops: OsOperations,
        kill_signal_id: T_KILL_SIGNAL_DESCR,
    ):
        """
        Test listdir for listing directory contents.
        """
        assert isinstance(os_ops, OsOperations)
        assert type(kill_signal_id) is tuple

        cmd = [
            sys.executable,
            "-c",
            "import time; print('ENTER');time.sleep(300);print('EXIT')"
        ]

        logging.info("Local test process is creating ...")
        proc = subprocess.Popen(
            cmd,
            text=True,
        )

        assert proc is not None
        assert type(proc) is subprocess.Popen
        proc_pid = proc.pid
        assert type(proc_pid) is int
        logging.info("Test process pid is {}".format(proc_pid))

        logging.info("Get this test process ...")
        p1 = psutil.Process(proc_pid)
        assert p1 is not None
        del p1

        logging.info("Kill this test process ...")
        os_ops.kill(proc_pid, kill_signal_id[1])

        logging.info("Wait for finish ...")
        proc.wait()

        logging.info("Try to get this test process ...")

        attempt = 0
        while True:
            if attempt == 20:
                raise RuntimeError("Process did not die.")

            attempt += 1

            if attempt > 1:
                logging.info("Sleep 1 seconds...")
                time.sleep(1)

            try:
                psutil.Process(proc_pid)
            except psutil.ZombieProcess as e:
                logging.info("Exception {}: {}".format(
                    type(e).__name__,
                    str(e),
                ))
            except psutil.NoSuchProcess:
                logging.info("OK. Process died.")
                break

            logging.info("Process is alive!")
            continue

        return

    def test_kill__unk_pid(
        self,
        os_ops: OsOperations,
        kill_signal_id: T_KILL_SIGNAL_DESCR,
    ):
        """
        Test listdir for listing directory contents.
        """
        assert isinstance(os_ops, OsOperations)
        assert type(kill_signal_id) is tuple

        cmd = [
            sys.executable,
            "-c",
            "import sys; print(\"a\", file=sys.stdout); print(\"b\", file=sys.stderr)"
        ]

        logging.info("Local test process is creating ...")
        proc = subprocess.Popen(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert proc is not None
        assert type(proc) is subprocess.Popen
        proc_pid = proc.pid
        assert type(proc_pid) is int
        logging.info("Test process pid is {}".format(proc_pid))

        logging.info("Wait for finish ...")
        pout, perr = proc.communicate()
        logging.info("STDOUT: {}".format(pout))
        logging.info("STDERR: {}".format(pout))
        assert type(pout) is str
        assert type(perr) is str
        assert pout == "a\n"
        assert perr == "b\n"
        assert type(proc.returncode) is int
        assert proc.returncode == 0

        logging.info("Try to get this test process ...")

        attempt = 0
        while True:
            if attempt == 20:
                raise RuntimeError("Process did not die.")

            attempt += 1

            if attempt > 1:
                logging.info("Sleep 1 seconds...")
                time.sleep(1)

            try:
                psutil.Process(proc_pid)
            except psutil.ZombieProcess as e:
                logging.info("Exception {}: {}".format(
                    type(e).__name__,
                    str(e),
                ))
            except psutil.NoSuchProcess:
                logging.info("OK. Process died.")
                break

            logging.info("Process is alive!")
            continue

        # --------------------
        with pytest.raises(expected_exception=Exception) as x:
            os_ops.kill(proc_pid, kill_signal_id[1])

        assert x is not None
        assert isinstance(x.value, Exception)
        assert not isinstance(x.value, AssertionError)

        logging.info("Our error is [{}]".format(str(x.value)))
        logging.info("Our exception has type [{}]".format(type(x.value).__name__))

        if type(os_ops).__name__ == "LocalOsOperations":
            assert type(x.value) is ProcessLookupError
            assert "No such process" in str(x.value)
        elif type(os_ops).__name__ == "RemoteOsOperations":
            assert type(x.value) is ExecUtilException
            assert "No such process" in str(x.value)
        else:
            RuntimeError("Unknown os_ops type: {}".format(type(os_ops).__name__))

        return

    def test_get_dirname(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        p = __file__
        assert type(p) is str
        assert p != ""
        assert os.path.exists(p)

        expected_dirname = os.path.dirname(p)
        assert type(expected_dirname) is str
        assert expected_dirname != ""

        actual_dirname = os_ops.get_dirname(p)
        assert type(actual_dirname) is str
        assert actual_dirname != ""

        assert actual_dirname == expected_dirname
        return

    def test_is_abs_path__yes(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        p = __file__
        assert type(p) is str
        assert p != ""
        assert os.path.isabs(p)

        actual_value = os_ops.is_abs_path(p)
        assert type(actual_value) is bool

        assert actual_value is True
        return

    def test_is_abs_path__no(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        p = "."
        assert not os.path.isabs(p)

        actual_value = os_ops.is_abs_path(p)
        assert type(actual_value) is bool

        assert actual_value is False
        return

    def test_get_process_children__no_children(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        sh_cmd = ["sh", "-c", "python3 -u -c 'import time;import os; print(os.getpid()); time.sleep(60)'"]

        p1 = os_ops.exec_command(
            sh_cmd,
            get_process=True,
            encoding="utf-8",
        )

        assert isinstance(p1, subprocess.Popen)
        assert p1.stdout is not None

        line = p1.stdout.readline()
        assert line is not None
        assert type(line) is str
        line = line.rstrip()
        assert line != ""
        logging.info("pid is {}".format(line))

        pid = int(line.rstrip())

        childs = os_ops.get_process_children(pid)
        assert childs is not None
        assert type(childs) is list
        assert len(childs) == 0
        return

    def test_get_process_children__with_child(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        script = (
            "import time, os, subprocess; "
            "s = str(os.getpid()); "
            "p = subprocess.Popen('exec sleep 60', shell=True, stdout=subprocess.PIPE, text=True); "
            "s += ':' + str(p.pid); "
            "print(s, flush=True); "
            "time.sleep(60)"
        )
        sh_cmd = ["python3", "-u", "-c", script]

        p1 = os_ops.exec_command(
            sh_cmd,
            get_process=True,
            encoding="utf-8",
        )

        assert isinstance(p1, subprocess.Popen)
        assert p1.stdout is not None
        p1.pid

        line = p1.stdout.readline()
        assert line is not None
        line = line.rstrip()
        assert line != ""

        # "PARENT_PID:CHILD_PID"
        parent_pid_str, expected_child_pid_str = line.split(":")
        parent_pid = int(parent_pid_str)
        expected_child_pid = int(expected_child_pid_str)

        logging.info(f"Parent PID from stdout: {parent_pid}")
        logging.info(f"Expected Child PID from stdout: {expected_child_pid}")

        # A short pause to ensure registration in the OS
        # time.sleep(0.5)

        childs = os_ops.get_process_children(parent_pid)

        assert childs is not None
        assert isinstance(childs, list)
        assert len(childs) == 1

        actual_child_pid = childs[0].pid
        logging.info(f"Actual Child PID from get_process_children: {actual_child_pid}")

        assert actual_child_pid == expected_child_pid

        p1.terminate()
        p1.wait()
        return

    def test_get_process_children__with_three_children(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        script = (
            "import time, os, subprocess; "
            "s = str(os.getpid()); "
            "p1 = subprocess.Popen('exec sleep 60', shell=True, stdout=subprocess.PIPE, text=True); "
            "p2 = subprocess.Popen('exec sleep 60', shell=True, stdout=subprocess.PIPE, text=True); "
            "p3 = subprocess.Popen('exec sleep 60', shell=True, stdout=subprocess.PIPE, text=True); "
            "s += ':' + str(p1.pid) + ':' + str(p2.pid) + ':' + str(p3.pid); "
            "print(s, flush=True); "
            "time.sleep(60)"
        )
        sh_cmd = ["python3", "-u", "-c", script]

        p = os_ops.exec_command(
            sh_cmd,
            get_process=True,
            encoding="utf-8",
        )

        assert isinstance(p, subprocess.Popen)
        assert p.stdout is not None

        line = p.stdout.readline()
        assert line is not None
        line = line.rstrip()
        assert line != ""

        parts = [int(x) for x in line.split(":")]
        parent_pid = parts[0]
        expected_child_pids = set(parts[1:])

        logging.info(f"Parent PID: {parent_pid}")
        logging.info(f"Expected Child PIDs: {expected_child_pids}")

        # A short pause to ensure registration in the OS
        # time.sleep(0.5)

        childs = os_ops.get_process_children(parent_pid)

        assert childs is not None
        assert isinstance(childs, list)
        assert len(childs) == 3

        actual_child_pids = {child.pid for child in childs}
        logging.info(f"Actual Child PIDs: {actual_child_pids}")

        assert actual_child_pids == expected_child_pids

        p.terminate()
        p.wait()
        return

    def test_get_process_children__bad_pid(self, os_ops: OsOperations):
        assert isinstance(os_ops, OsOperations)

        C_BAD_PID = 999999876  # OK? ))

        with pytest.raises(expected_exception=Exception) as x:
            os_ops.get_process_children(999999876)

        if type(os_ops).__name__ == "LocalOperations":
            assert type(x.value) is psutil.NoSuchProcess
            assert x.value.pid == C_BAD_PID
        elif type(os_ops).__name__ == "RemoteOperations":
            assert type(x.value) is ExecUtilException
            msg1 = "Failed to get process children. Reason: No such process with PID {}.".format(
                C_BAD_PID,
            )
            assert msg1 in str(x)
            assert x.value.exit_code == 1
        else:
            raise RuntimeError("[BUG CHECK] Unknown os_ops type [{}]".format(
                type(os_ops).__name__,
            ))
        return
