import os
from celery import Celery

# Create Celery app
app = Celery('financial_analyzer')

# Configuration
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_routes={
        'celery_worker.*': {'queue': 'default'}
    },
    # Windows compatibility settings
    worker_pool='solo' if os.name == 'nt' else 'prefork',
    worker_concurrency=1,
)

if __name__ == '__main__':
    app.start()