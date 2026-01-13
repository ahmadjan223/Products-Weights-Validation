import os

# Use ASGI worker so FastAPI receives ASGI-style scope/receive/send
worker_class = "uvicorn.workers.UvicornWorker"

host = "0.0.0.0"
port = os.getenv("PORT", "8080")
bind = f"{host}:{port}"

workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = int(os.getenv("PYTHON_GUNICORN_THREADS", "8"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
