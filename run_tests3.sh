#!/bin/bash
set -eux

for i in {2..11}; do
    sudo ip addr add 127.0.0.$i/32 dev lo
done

# prepare python environment
VENV_PATH="/tmp/testgres_venv"
rm -rf $VENV_PATH
${PYTHON_BINARY} -m venv "${VENV_PATH}"
export VIRTUAL_ENV_DISABLE_PROMPT=1
source "${VENV_PATH}/bin/activate"
pip install --upgrade pip setuptools wheel
${PYTHON_BINARY} -m pip install -r tests/requirements.txt

export -p

# run builtin tests
${PYTHON_BINARY} -m pytest -l -vvv -n 4

set +eux
