python -m pip install --user virtualenv --proxy=%http_proxy%
python -m virtualenv venv
call venv\Scripts\activate.bat
python -m pip install -r requirements.txt --proxy=%http_proxy%

echo "pour activer l'environnement, taper :"
echo "venv\Scripts\activate"