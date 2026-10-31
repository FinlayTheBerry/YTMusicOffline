#!/bin/sh

cd "$(dirname "$0")"

if [ ! -d "env" ]; then
    python3 -m venv env
    source env/bin/activate
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
fi

source env/bin/activate
exec python3 ytmusic-dl.py
