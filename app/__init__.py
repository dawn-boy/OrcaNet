from flask import Flask
from celery import Celery, Task
from flask_htmx import HTMX
import os

def create_app():
    app = Flask(__name__)
    htmx = HTMX(app)
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')


    app.config.from_mapping(
        CELERY=dict(
            broker_url=redis_url,
            result_backend=redis_url,
            task_serializer='pickle',
            result_serializer='pickle',
            accept_content=['pickle', 'json'],
        )
    )
    celery_init_app(app)

    from . import routes
    app.register_blueprint(routes.bp)

    return app

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
