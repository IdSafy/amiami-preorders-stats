#/bin/sh

export PYTHONPATH=$PYTHONPATH:./src/

exec python -m uvicorn amiami_api.web:app --host 0.0.0.0 --port 8000
