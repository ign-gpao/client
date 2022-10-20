#!/bin/bash

python3 -m pip install --user virtualenv
python3 -m virtualenv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt

echo "pour activer l'environnement, taper :"
echo "source venv/bin/activate"