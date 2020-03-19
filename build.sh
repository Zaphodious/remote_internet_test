#!/bin/bash
. goenv
pip install pyinstaller
pyinstaller testinternet.py -F
. endenv