#!/bin/bash

THIS_DIR="$(dirname ${BASH_SOURCE[0]})"
cd "$THIS_DIR"

# update from remote
git pull

# run server
exec pipenv run python3 "${THIS_DIR}/app.py"
