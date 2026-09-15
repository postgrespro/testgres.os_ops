# //////////////////////////////////////////////////////////////////////////////
from __future__ import annotations

import os
import typing
import logging


# //////////////////////////////////////////////////////////////////////////////

def _debug_print(tmpl: str, *args) -> None:
    assert type(tmpl) is str
    s = tmpl.format(*args)
    logging.debug("[testgres.os_ops] DEBUG: {}".format(s))
    return


# ------------------------------------------------------------------------
def _setup_new_cfg_opt_value(
    env_param_name: str,
    value: typing.Any,
) -> typing.Any:
    assert type(env_param_name) is str
    _debug_print(
        "New value for cfg option {} is used: {!r}",
        env_param_name,
        value,
    )
    return value


# ------------------------------------------------------------------------
def _get_opt_float(
    default_value: float,
    env_param_name: str,
    min_value: float,
    max_value: float,
) -> float:
    assert type(default_value) is float
    assert type(env_param_name) is str
    assert type(min_value) is float
    assert type(max_value) is float

    env_val = os.environ.get(env_param_name)

    if env_val is None:
        return default_value

    try:
        val = float(env_val)
    except ValueError:
        _debug_print(
            "Cfg property {} has wrong value {!r}. Default value is used {}.",
            env_param_name,
            env_val,
            default_value,
        )
        return default_value

    assert type(val) is float

    if val < min_value or max_value < val:
        _debug_print(
            "Cfg property {} has out of range value {}. Valid range is [{}..{}]. Default value {} is used.",
            env_param_name,
            val,
            min_value,
            max_value,
            default_value,
        )
        return default_value

    return _setup_new_cfg_opt_value(
        env_param_name,
        val,
    )


# //////////////////////////////////////////////////////////////////////////////
# OsOperationStaticConfig

class OsOperationStaticConfig:
    remote_ops__popen__handshake_timeout = _get_opt_float(
        10.0,
        "TESTGRES_OS_OPS_CFG__REMOTE_OPS__POPEN__HANDSHAKE_TIMEOUT",
        5.0,
        4 * 3600.0,
    )

# //////////////////////////////////////////////////////////////////////////////
