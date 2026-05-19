#!/bin/bash
set -e

cd /home/-

echo "=== رَوْنَق Dashboard ==="
echo "Installing dependencies..."
pip3 install -q -r requirements_dashboard.txt

echo "Starting dashboard on http://0.0.0.0:3002 ..."
python3 dashboard_server.py
