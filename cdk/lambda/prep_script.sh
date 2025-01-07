pip install pydantic -t cdk/lambda/layer/python/lib/python3.12/site-packages --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 
pip install -r cdk/lambda/layer/requirements.txt -t cdk/lambda/layer/python/lib/python3.12/site-packages
cp docker/app/src/models/params.py cdk/lambda/src
cp docker/app/src/models/pynamodb_models.py cdk/lambda/src/
cp docker/app/src/config/settings.py cdk/lambda/src/
