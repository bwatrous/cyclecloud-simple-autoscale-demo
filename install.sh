#!/bin/bash

python3 -m venv ~/.virtualenvs/autoscale_demo
. ~/.virtualenvs/autoscale_demo/bin/activate
pip install -U pip
pip install ./packages/*
pip install retry

    
