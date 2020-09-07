#!/bin/bash
python3 -m PyQt5.uic.pyuic -x layouts/widget.ui -o widget.py
python3 -m PyQt5.uic.pyuic -x layouts/about.ui -o about.py

