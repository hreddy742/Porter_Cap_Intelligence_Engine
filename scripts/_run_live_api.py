import sys

sys.path[:0] = [
    r"C:\Users\hreddy\Search Intelligence\.runtime-live",
    r"C:\Users\hreddy\Search Intelligence\src",
]

from uvicorn.config import Config  # noqa: E402
from uvicorn.server import Server  # noqa: E402

Server(Config("porter_verify.api.app:app", host="0.0.0.0", port=8000)).run()
