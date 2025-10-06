import os

port = os.getenv("PORT", "5000")
bind = f"0.0.0.0:{port}"
workers = 4

