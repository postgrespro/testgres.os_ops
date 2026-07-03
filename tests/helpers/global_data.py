from src.os_ops import OsOperations
from src.os_ops import ConnectionParams
from src.local_ops import LocalOperations
from src.remote_ops import RemoteOperations

import os


class OsOpsDescr:
    sign: str
    os_ops: OsOperations

    def __init__(self, sign: str, os_ops: OsOperations):
        assert type(sign) is str
        assert isinstance(os_ops, OsOperations)
        self.sign = sign
        self.os_ops = os_ops


class OsOpsDescrs:
    sm_remote_conn_params = ConnectionParams(
        host=os.getenv('TEST_PARAM_REMOTE2_HOST') or '127.0.0.1',
        username=os.getenv('TEST_PARAM_REMOTE2_USERNAME'),
        ssh_key=os.getenv('TEST_PARAM_REMOTE2_SSH_KEY'),
        password=os.getenv('TEST_PARAM_REMOTE2_PASSWORD'),
    )

    sm_remote_os_ops = RemoteOperations(sm_remote_conn_params)

    sm_remote_os_ops_descr = OsOpsDescr("remote_ops", sm_remote_os_ops)

    sm_local_os_ops = LocalOperations.get_single_instance()

    sm_local_os_ops_descr = OsOpsDescr("local_ops", sm_local_os_ops)
