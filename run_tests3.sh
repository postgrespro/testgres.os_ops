#!/bin/bash
set -eux

if [ -z ${TEST_FILTER+x} ]; \
then export TEST_FILTER=""; \
fi

# prepare python environment
VENV_PATH="/tmp/testgres_venv"
rm -rf $VENV_PATH
${PYTHON_BINARY} -m venv "${VENV_PATH}"
export VIRTUAL_ENV_DISABLE_PROMPT=1
source "${VENV_PATH}/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r tests/requirements.txt

export -p

# run builtin tests
pytest -l -vvv -n 4 --color=yes -k "${TEST_FILTER}"

set +eux
