import socket
import threading
import time
import json
from webserver1 import handle_client, USERS
from concurrent.futures import ThreadPoolExecutor

def read_http_response(client: socket.socket) -> tuple[bytes, bytes]:
    response = b""

    while True:
        chunk = client.recv(1024)

        if not chunk:
            break

        response += chunk

    if b"\r\n\r\n" not in response:
        raise ValueError(
            "Invalid HTTP response: headers separator not found"
        )

    headers, body = response.split(b"\r\n\r\n", 1)

    return headers, body


def test_health_over_tcp(tcp_listener):
    
    server, port = tcp_listener
    def serve_one_client():
        conn, address = server.accept()
        handle_client(conn)

    worker = threading.Thread(target=serve_one_client)
    worker.start()
    with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
        request = (
            b"GET /health HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"\r\n"
        )
        request_body = b""
        buffer = request + request_body
        client.sendall(buffer)
        headers, body = read_http_response(client)
        assert headers.startswith(b"HTTP/1.1 200 OK")
        assert b"Content-Length: 2\r\n" in headers + b"\r\n"
        assert body == b"OK"

    worker.join(timeout=3)
    assert not worker.is_alive()

def test_post_fragmented_body_over_tcp(tcp_listener):
    server, port = tcp_listener

    def serve_one_client():
        conn, address = server.accept()
        handle_client(conn)
    worker = threading.Thread(target=serve_one_client)
    worker.start()
    with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
        body = json.dumps({"name": "Alice"}).encode("utf-8")
        headers = (
            b"POST /users HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("ascii")
            + b"\r\n"
        )
        first_part = headers + body[:7]
        second_part = body[7:]
        client.sendall(first_part)
        time.sleep(0.1)
        client.sendall(second_part)
        headers, body = read_http_response(client)
        assert headers.startswith(b"HTTP/1.1 201 Created")
        test_json = json.dumps({
            "id": 1,
            "name": "Alice"
            }).encode("utf-8")
        length = len(test_json)
        assert f"Content-Length: {length}\r\n".encode("utf-8") in headers + b"\r\n"
        payload = json.loads(body)
        assert payload == {
            "id": 1,
            "name": "Alice",
        }
        assert len(USERS) == 1
        assert b"application/json" in headers
        assert len(USERS) == 1
        assert USERS[0]["id"] == 1
        assert USERS[0]["name"] == "Alice"
    worker.join(timeout=3)
    assert not worker.is_alive()


def create_user(index, port):
    with socket.create_connection(
        ("127.0.0.1", port),
        timeout=5.0
    ) as client:
        body = json.dumps({"name": f"User-{index}"}).encode("utf-8")
        
        headers = (
            b"POST /users HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("ascii")
            + b"\r\n"
        )

        request = headers + body

        client.sendall(request)
        headers, body = read_http_response(client)
        payload = json.loads(body)

        return headers, payload

def test_concurrent_user_creation(tcp_listener):
    server, port = tcp_listener

    def serve_clients():
        workers = []
        for _ in range(50):
            conn, address = server.accept()
            worker = threading.Thread(
                target=handle_client,
                args=(conn,)
            )
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join(timeout=5)
            assert not worker.is_alive()

    with ThreadPoolExecutor(max_workers=1) as server_executor:
        server_future = server_executor.submit(serve_clients)
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(
                executor.map(
                    lambda index: create_user(index, port),
                    range(50)
                )
            )
            for headers, payload in results:
                assert headers.startswith(b"HTTP/1.1 201 Created\r\n")
                assert isinstance(payload["id"], int)
        server_future.result(timeout=10)

    # Только теперь серверный socket закрывается.

    assert len(USERS) == 50

    ids = [user["id"] for user in USERS]
    response_ids = [payload["id"] for _, payload in results]

    assert sorted(ids) == list(range(1, 51))
    assert sorted(response_ids) == list(range(1, 51))