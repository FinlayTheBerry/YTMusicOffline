#!/bin/sh

cd "$(dirname "$0")"

if [ ! -d "env" ]; then
    python -m venv env
    source env/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
fi

source env/bin/activate
exec python downloader.py
