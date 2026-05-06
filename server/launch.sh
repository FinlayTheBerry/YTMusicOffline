#!/bin/sh

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    python -m venv venv
    source venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
fi

source venv/bin/activate
exec python server.py