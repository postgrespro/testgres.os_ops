[![CI Status](https://img.shields.io/github/actions/workflow/status/postgrespro/testgres.os_ops/.github/workflows/ci.yml?label=CI)](https://github.com/postgrespro/testgres.os_ops/actions/workflows/ci.yml)
[![PyPI package version](https://badge.fury.io/py/testgres_os_ops.svg)](https://badge.fury.io/py/testgres.os_ops)
[![PyPI python versions](https://img.shields.io/pypi/pyversions/testgres_os_ops)](https://pypi.org/project/testgres.os-ops)
[![PyPI downloads](https://img.shields.io/pypi/dm/testgres_os_ops)](https://pypi.org/project/testgres.os-ops)

# testgres.os_ops

`testgres.os_ops` is a lightweight Python package that provides a unified, highly secure, and polymorphic interface (`OsOperations`) for interacting with the operating system environment either locally or on a remote machine.

While originally designed as an infrastructure core for the **testgres** PostgreSQL testing framework, this package is completely decoupled and can be installed and used independently in any automation pipeline.

---

## Key Features

* **Unified API (`OsOperations`)**: Write your automation logic once using a high-level abstract interface and switch transparently between local execution and remote SSH sessions.
* **Stateless and Stateful Environments**: Smooth handling of environment variables across distinct execution contexts (`set_env`, `environ`, and polymorphic `reset_env` with clean state rollback).
* **Industrial-Grade Shell Security**: Safe execution pipeline featuring bulletproof shell argument escaping (`join_command_arguments`) and tilde tracking (`~`, `~root`), fully eliminating code injection vulnerabilities.
* **Cross-Platform Consistency**: Extensively verified via a robust multi-container matrix across 12+ Linux distributions (including Ubuntu, Rocky Linux, Alt Linux, Astra Linux, and Alpine).

---

## Installation

```bash
pip install testgres.os-ops
```

---

## Architecture

* **`LocalOperations`**: Interacts with the host machine using native Python standard libraries (`subprocess`, `psutil`, `os`, `pathlib`).
* **`RemoteOperations`**: Controls remote Linux-based nodes by proxying commands over secure SSH connections (utilizing binary stream polling and automated environment replication).

Supported operation groups include:
* Safe shell command execution
* Persistent environment variable tracking
* File and directory tree management (`stat`, exclusive creation, copying)
* Process lifecycle and signal management

---

## Quick Start Example

The following example demonstrates how the exact same generic automation code executes seamlessly on both a local host and a remote RHEL server.

```python
import uuid
from testgres.operations.os_ops import OsOperations
from testgres.operations.os_ops import ConnectionParams
from testgres.operations.local_ops import LocalOperations
from testgres.operations.remote_ops import RemoteOperations


def generic_pipeline(title: str, os_ops: OsOperations):
    """Polymorphic code that executes identically on any target platform."""
    cmd = [
        "sh",
        "-c",
        "echo whoami: $(whoami); "
        "echo \"------ os_info:\"; cat /etc/os-release; "
        "echo \"------ our env:\"; echo \"OS_OPS_ENV\": ${OS_OPS_ENV}; "
    ]
    print("[{}] -------------\n".format(title))

    # Set stateful environment variable
    os_ops.set_env("OS_OPS_ENV", "HELLO WORLD!")

    # Safe execution with precise encoding
    cout = os_ops.exec_command(cmd, encoding="utf-8")
    print(cout)

    # Polymorphic state cleanup
    os_ops.reset_env("OS_OPS_ENV", None)
    return


# 1. Run locally using Python API under the hood
local_ops = LocalOperations()
generic_pipeline("Local system", local_ops)

# 2. Run remotely over an isolated SSH session
remote_cn_params = ConnectionParams(
    host="192.168.122.85",
    port=22,
    username="test",
    ssh_key="./id_rsa_test",
)
remote_ops = RemoteOperations(remote_cn_params)
generic_pipeline("Remote system", remote_ops)
```

### Expected Output

```text
[Local system] -------------

whoami: dima
------ os_info:
PRETTY_NAME="Ubuntu 24.04.4 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.4 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://ubuntu.com"
SUPPORT_URL="https://ubuntu.com"
BUG_REPORT_URL="https://launchpad.net"
PRIVACY_POLICY_URL="https://ubuntu.comlegal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
------ our env:
OS_OPS_ENV: HELLO WORLD!

[Remote system] -------------

whoami: test
------ os_info:
NAME="Red Hat Enterprise Linux"
VERSION="8.9 (Ootpa)"
ID="rhel"
ID_LIKE="fedora"
VERSION_ID="8.9"
PLATFORM_ID="platform:el8"
PRETTY_NAME="Red Hat Enterprise Linux 8.9 (Ootpa)"
ANSI_COLOR="0;31"
CPE_NAME="cpe:/o:redhat:enterprise_linux:8::baseos"
HOME_URL="https://redhat.com"
DOCUMENTATION_URL="https://redhat.com"
BUG_REPORT_URL="https://redhat.com"

REDHAT_BUGZILLA_PRODUCT="Red Hat Enterprise Linux 8"
REDHAT_BUGZILLA_PRODUCT_VERSION=8.9
REDHAT_SUPPORT_PRODUCT="Red Hat Enterprise Linux"
REDHAT_SUPPORT_PRODUCT_VERSION="8.9"
------ our env:
OS_OPS_ENV: HELLO WORLD!
```

---

## Testing

The project includes an intensive full-scale test suite ensuring absolute behavior consistency between local and remote providers. The validation matrix automatically deploys multi-container Docker environments to stress-test concurrent setups, edge-case quoting anomalies, and thread isolation across distinct architectures.

## Authors

[Postgres Professional](https://postgrespro.ru/about)
