#!/bin/bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Collect static files into staticfiles directory
python3 manage.py collectstatic --noinput
