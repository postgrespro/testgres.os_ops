# coding: utf-8
from __future__ import annotations

from src.os_ops import ConnectionParams


class TestConnectionParams:
    def test_default(self):
        cp = ConnectionParams()

        assert cp.host == "127.0.0.1"
        assert cp.port is None
        assert cp.ssh_key is None
        assert cp.username is None
        return

    def test_init(self):
        cp = ConnectionParams(
            host="localhost",
            port=123,
            ssh_key="id_rsa",
            username="test"
        )

        assert cp.host == "localhost"
        assert cp.port == 123
        assert cp.ssh_key == "id_rsa"
        assert cp.username == "test"
        return
