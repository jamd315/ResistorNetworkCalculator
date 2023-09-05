#!/bin/bash
python3 resistor_combinatorics.py
gunicorn --bind 0.0.0.0:80 -t 600 resistor_network_server:app