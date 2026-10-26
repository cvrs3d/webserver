from webserver1 import build_http_response, route_request, USERS, ClientError
import pytest
import json
from conftest import reset_users

def test_response_200():
    response = build_http_response(
        200,
        b"Hello World!"
    )

    assert response.startswith(
        b"HTTP/1.1 200 OK\r\n"
    )

    assert b"Content-Length: 12\r\n" in response

    assert response.endswith(
        b"\r\n\r\nHello World!"
    )

def test_response_empty_200():
    response = build_http_response(
            200,
            b""
    )

    assert response.startswith(
            b"HTTP/1.1 200 OK\r\n"
    )

    assert b"Content-Length: 0\r\n" in response

    assert response.endswith(b"\r\n\r\n")

def test_response_404():
    response = build_http_response(
                404,
                b"Not Found"
    )

    assert response.startswith(
                b"HTTP/1.1 404 Not Found\r\n"
    )

    assert b"Content-Length: 9\r\n" in response
    
    assert response.endswith(
            b"\r\n\r\nNot Found"
    )

def test_unsupported_status_code():
    with pytest.raises(ValueError):
        build_http_response(999, b"Test")

def test_response_post_201():
    response = build_http_response(
         201,
         json.dumps({
              "id": 1,
              "name": "Test"
         }).encode("utf-8"),
         "application/json"
    )
    assert response.startswith(
         b"HTTP/1.1 201 Created\r\n"
    )
    test_json = json.dumps({
         "id": 1,
         "name": "Test"
    }).encode("utf-8")
    headers, body = response.split(b"\r\n\r\n", 1)
    assert body == test_json
    assert f"Content-Length: {len(body)}\r\n".encode() in headers + b"\r\n"
    assert b"application/json" in response

def test_get_health():
    request = {
        "method": "GET",
        "path": "/health"
    }

    response = route_request(request, b"")

    assert response.startswith(b"HTTP/1.1 200 OK\r\n")
    assert response.endswith(b"\r\n\r\nOK")

def test_get_unknown_route():
    request = {
        "method": "GET",
        "path": "/unknown"
    }

    response = route_request(request, b"")

    assert response.startswith(b"HTTP/1.1 404 Not Found\r\n")
    assert response.endswith(b"\r\n\r\nNot Found")
    assert b"Content-Length: 9\r\n" in response

def test_post_user():
    request = {
        "method": "POST",
        "path": "/users"
    }

    body = json.dumps({
        "name": "Alice"
    }).encode("utf-8")

    response = route_request(request, body)

    assert response.startswith(b"HTTP/1.1 201 Created\r\n")
    test_json = json.dumps({
             "id": 1,
             "name": "Alice"
        }).encode("utf-8")
    headers, body = response.split(b"\r\n\r\n", 1)
    assert body == test_json
    assert f"Content-Length: {len(body)}\r\n".encode() in headers + b"\r\n"
    assert b"application/json" in response
    assert len(USERS) == 1
    assert USERS[0]["id"] == 1
    assert USERS[0]["name"] == "Alice"

def test_post_invalid_json():
    request = {
        "method": "POST",
        "path": "/users"
    }

    body = b'{"name":'

    with pytest.raises(ClientError, match="Invalid JSON body"):
        route_request(request, body)

def test_post_missing_name():
    request = {
            "method": "POST",
            "path": "/users"
    }
    body = json.dumps({
    }).encode("utf-8")

    with pytest.raises(ClientError):
        response = route_request(request, body)

def test_users_api():
    # Add Alice with POST 
    request = {
        "method": "POST",
        "path": "/users"
    }

    body = json.dumps({
        "name": "Alice"
    }).encode("utf-8")

    response = route_request(request, body)

    assert response.startswith(b"HTTP/1.1 201 Created\r\n")
    test_json = json.dumps({
             "id": 1,
             "name": "Alice"
        }).encode("utf-8")
    headers, body = response.split(b"\r\n\r\n", 1)
    assert body == test_json
    assert f"Content-Length: {len(body)}\r\n".encode() in headers + b"\r\n"
    assert b"application/json" in response
    assert len(USERS) == 1
    assert USERS[0]["id"] == 1
    assert USERS[0]["name"] == "Alice"

    # add Bob
    request = {
        "method": "POST",
        "path": "/users"
    }

    body = json.dumps({
        "name": "Bob"
    }).encode("utf-8")

    response = route_request(request, body)

    assert response.startswith(b"HTTP/1.1 201 Created\r\n")
    test_json = json.dumps({
             "id": 2,
             "name": "Bob"
        }).encode("utf-8")
    headers, body = response.split(b"\r\n\r\n", 1)
    assert body == test_json
    assert f"Content-Length: {len(body)}\r\n".encode() in headers + b"\r\n"
    assert b"application/json" in response
    assert len(USERS) == 2
    assert USERS[1]["id"] == 2
    assert USERS[1]["name"] == "Bob"

    # GET /users

    request = {
        "method": "GET",
        "path": "/users"
    }

    response = route_request(request, b"")
    assert response.startswith(b"HTTP/1.1 200 OK\r\n")
    headers, body = response.split(b"\r\n\r\n", 1)

    assert f"Content-Length: {len(body)}\r\n".encode() in headers + b"\r\n"
    assert b"application/json" in response

    body_decode = json.loads(body)
    assert isinstance(body_decode, dict)

    users = body_decode["users"]

    assert users == [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
    ]
    
def test_method_not_allowed():
    request = {
        "method": "DELETE",
        "path": "/users"
    }

    response = route_request(request, b"")

    assert response.startswith(
        b"HTTP/1.1 405 Method Not Allowed\r\n"
    )

    assert b"Allow: GET, POST\r\n" in response



