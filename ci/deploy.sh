python setup.py sdist
pip install twine
twine check dist/*
twine upload dist/*
