import pytest
from webserver1 import USERS, USERS_LOCK
import socket


@pytest.fixture(autouse=True)
def reset_users():
    with USERS_LOCK:
        USERS.clear()

    yield

    with USERS_LOCK:
        USERS.clear()

@pytest.fixture
def tcp_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(5.0)

        port = server.getsockname()[1]
        yield server, port