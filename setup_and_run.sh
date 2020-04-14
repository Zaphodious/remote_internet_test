#!/bin/bash

python3 -m venv env
chmod a+x testinternet.py
chmod a+x build.sh
. goenv
pip install -r requirements.txt
./testinternet.py
