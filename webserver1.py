import socket
import json
import threading   

class ClientError(ValueError):
    pass

MAX_HEADERS_SIZE = 16 * 1024
MAX_BODY_SIZE = 1024 * 1024

HTTP_CODES = {
    200: "OK",
    201: "Created",
    404: "Not Found",
    400: "Bad Request",
    405: "Method Not Allowed",
}
USERS = []
USERS_LOCK = threading.Lock()
ROUTES = {
    "/": "Welcome!",
    "/health": "OK",
    "/users": {"users": USERS},
}
ALLOWED_METHODS = {
    "/": {"GET"},
    "/health": {"GET"},
    "/users": {"GET", "POST"},
}


def api_users(body: bytes, method: str, path: str = "/users"):
    content_type = "application/json"
    if method == "GET":
        with USERS_LOCK:
            users_snapshot = list(USERS)

        j_string = json.dumps({"users": users_snapshot})
        response = j_string.encode("utf-8")
        return build_http_response(200, response, content_type)
    if method == "POST":
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ClientError("Invalid JSON body") from exc
        
        if not isinstance(data, dict):
            raise ClientError("JSON body must be an object")

        name = data.get("name")

        if not isinstance(name, str) or not name.strip():
            raise ClientError("Field 'name' must be a non-empty string")

        with USERS_LOCK:
            response = {
                "id": len(USERS) + 1,
                "name": name,
            }

            USERS.append(response)

        response = json.dumps(response).encode("utf-8")

        return build_http_response(201, response, content_type)

    return build_http_response(404, body)

        


def route_request(request: dict, request_data: bytes) -> bytes:
    path = request["path"]
    method = request["method"]
    if path not in ROUTES:
        body = HTTP_CODES[404].encode("utf-8")
        return build_http_response(404, body)
    if method not in ALLOWED_METHODS[path]:
        body = HTTP_CODES[405].encode("utf-8")
        return build_http_response(405, body, path=path)
    if path == "/users":
        return api_users(request_data, method, path)
    body = ROUTES[path].encode("utf-8")
    
    return build_http_response(200, body)

    

def build_http_response(
    status_code: int,
    body: bytes,
    content_type: str = "text/plain; charset=utf-8",
    path: str = "",
) -> bytes:
    if status_code not in HTTP_CODES:
        raise ValueError(f"No such code: {status_code}")
    response = ""
    first_line = f"HTTP/1.1 {status_code} {HTTP_CODES[status_code]}\r\n"
    content_length = len(body)
    response += first_line
    content_type_line = f"Content-Type: {content_type}\r\n"
    response += content_type_line
    content_length_line = f"Content-Length: {content_length}\r\n"
    response += content_length_line
    if status_code == 405:
        allowed = ALLOWED_METHODS.get(path, {"GET"})
        allowed_str = ", ".join(sorted(allowed))
        response += f"Allow: {allowed_str}\r\n"
    connection_line = "Connection: close\r\n\r\n"
    response += connection_line

    response = response.encode("utf-8")
    response += body
    return response

def read_http_body(conn, content_length_str, request_data) -> bytes:
    try:
        content_length = int(content_length_str)
    except ValueError:
        raise ClientError("Invalid Content-Length")

    if content_length < 0:
        raise ClientError("Negative Content-Length")

    if content_length > MAX_BODY_SIZE:
        raise ClientError("Too big Content-Length")
    body = request_data[:content_length]

    while len(body) < content_length:
        remaining = content_length - len(body)

        chunk = conn.recv(remaining)

        if not chunk:
            raise ConnectionError("Incomplete HTTP body")

        body += chunk

    return body


def read_http_req(conn):
    # Read whole HTTP request 
    buffer = b""
    while True:
        # read part of TCP byte stream
        chunk = conn.recv(1024)
        if not chunk:
            raise ConnectionError(
                "Connection closed before HTTP headers completed"
            )
        buffer += chunk
        end = buffer.find(b"\r\n\r\n")

        if end != -1:
            if end + 4 > MAX_HEADERS_SIZE:
                raise ClientError("HTTP header is too large")
            break
        if len(buffer) > MAX_HEADERS_SIZE:
            raise ClientError("HTTP header is too large")

    end_of_header = buffer.find(b"\r\n\r\n")

    header_encoded = buffer[0:end_of_header]

    try:
        header_data = header_encoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClientError("Invalid HTTP headers") from exc

    request_data = buffer[end_of_header + 4:]

    return header_data, request_data



def parse_http_request(conn):
    first_line = {}
    headers = {}
    request = read_http_req(conn)

    lines = request[0].split("\r\n")
    parts = lines[0].split()

    if len(parts) != 3:
        raise ClientError("Invalid HTTP request line")
    headers_unparsed = lines[1:]

    # Parse first line
    first_line["method"] = parts[0]
    first_line["path"] = parts[1]
    first_line["version"] = parts[2]

    for value in headers_unparsed:
        if ":" not in value:
            raise ClientError(f"Invalid HTTP header line in {value}")
        k, v = value.split(":", 1)
        k = k.lower().strip()
        v = v.strip()

        headers[k] = v

    first_line["headers"] = headers
    content_length_str = headers.get("content-length", "0")
    body = read_http_body(conn, content_length_str, request[1])
    return first_line, body


def handle_client(client_connection):
    with client_connection as conn:
        conn.settimeout(5.0)
        try:
            request_header, request_data = parse_http_request(conn=conn)
            print(f"Header: \n{request_header}")
            http_response = route_request(request_header, request_data)
            conn.sendall(http_response)
        except ConnectionError as exc:
            print(f"Client connection error: {exc}")
            return 
        except ClientError as exc:
            response = build_http_response(
                400,
                str(exc).encode("utf-8")
            )
            conn.sendall(response)
        except ValueError as exc:
            print(f"Client connection error: {exc}")
            return 
        except socket.timeout:
            print("Client connection timed out")
            return


def main():

    HOST, PORT = "127.0.0.1", 8888

    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind((HOST, PORT))
    listen_socket.listen(128)
    print(f"Listening HTTP on port {PORT} ...")
    while True:
        client_connection, client_address = listen_socket.accept()
        t = threading.Thread(target=handle_client, args=(client_connection,))
        t.start()


if __name__ == "__main__":
    main()