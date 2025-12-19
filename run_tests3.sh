#!/usr/bin/env bash

# Copyright (c) 2017-2025 Postgres Professional

set -eux

# prepare python environment
VENV_PATH="/tmp/testgres_venv"
rm -rf $VENV_PATH
python -m venv "${VENV_PATH}"
export VIRTUAL_ENV_DISABLE_PROMPT=1
source "${VENV_PATH}/bin/activate"
pip install -r tests/requirements.txt

# install testgres' dependencies
export PYTHONPATH=$(pwd)
# $PIP install .

flake8

pytest -l -v -n 4

set +eux

