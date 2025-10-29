# gunicorn_conf.py
from multiprocessing import cpu_count

bind = "127.0.0.1:8000"

# Worker Options
workers = cpu_count() + 1
worker_class = 'uvicorn.workers.UvicornWorker'

# Logging Options
loglevel = 'debug'
#accesslog = '/var/log/nginx/freak_access.log'
#errorlog = '/var/log/nginx/error.log'
accesslog = '/tmp/soundcork_access.log'
errorlog = '/tmp/soundcork_error.log'
