#!/usr/bin/env bash

set -eux

# prepare python environment
VENV_PATH="/tmp/testgres_venv"
rm -rf $VENV_PATH
python -m venv "${VENV_PATH}"
export VIRTUAL_ENV_DISABLE_PROMPT=1
source "${VENV_PATH}/bin/activate"
pip install -r tests/requirements.txt

# check code style
flake8 .

# run builtin tests
python -m pytest -l -vvv -n 4

set +eux

