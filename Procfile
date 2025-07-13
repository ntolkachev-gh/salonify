web: gunicorn salonify.wsgi --log-file -
worker: celery -A salonify worker -l info
beat: celery -A salonify beat -l info 