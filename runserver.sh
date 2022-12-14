#!/bin/sh

python -m gunicorn grove.asgi:application -k uvicorn.workers.UvicornWorker
