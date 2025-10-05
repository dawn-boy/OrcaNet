# app/__init__.py
from flask import Flask
from flask_htmx import HTMX
from celery import Celery, Task


def create_app():
    app = Flask(__name__)
    htmx = HTMX(app)

    # Initialize Celery
    app.config.from_mapping(
        CELERY=dict(
            broker_url="redis://redis:6379/0",
            result_backend="redis://redis:6379/0",
            task_ignore_result=True,
        )
    )
    celery_init_app(app)

    # Register routes
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