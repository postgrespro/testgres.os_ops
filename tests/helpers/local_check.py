# coding: utf-8
from .os_ops_helpers import OsOpsHelpers
from .os_ops_helpers import OsOperations

import os


class LocalCheck:
    @staticmethod
    def check_path_exists(
        os_ops: OsOperations,
        path: str,
    ) -> None:
        assert isinstance(os_ops, OsOperations)
        assert type(path) is str

        if not OsOpsHelpers.is_localhost(os_ops):
            return

        if os.path.exists(path):
            return

        err_msg = "[LocalCheck] Local path [{}] does not exist.".format(
            path,
        )
        raise RuntimeError(err_msg)

    # --------------------------------------------------------------------
    @staticmethod
    def check_path_does_not_exists(
        os_ops: OsOperations,
        path: str,
    ) -> None:
        assert isinstance(os_ops, OsOperations)
        assert type(path) is str

        if not OsOpsHelpers.is_localhost(os_ops):
            return

        if not os.path.exists(path):
            return

        err_msg = "[LocalCheck] Local path [{}] exists.".format(
            path,
        )
        raise RuntimeError(err_msg)
