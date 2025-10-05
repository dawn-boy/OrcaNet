from flask import Flask
from celery import Celery, Task
from flask_htmx import HTMX


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    htmx = HTMX(app)


    # Configure Celery to use a robust serializer
    app.config.from_mapping(
        CELERY=dict(
            broker_url="redis://redis:6379/0",
            result_backend="redis://redis:6379/0",
            task_serializer='pickle',
            result_serializer='pickle',
            accept_content=['pickle', 'json'],
        )
    )
    celery_init_app(app)

    # Import and register your routes from routes.py
    from . import routes
    app.register_blueprint(routes.bp)

    return app


def celery_init_app(app: Flask) -> Celery:
    """Initialize Celery and integrate it with the Flask app context."""

    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app