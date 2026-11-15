# Python HTTP Server

A small HTTP server built directly with Python sockets and threads. The project explores how a TCP byte stream becomes an HTTP request, how responses are framed, and how concurrent requests share application state.

This is an educational implementation with partial HTTP/1.1 support.

## Implemented behavior

- Reads headers and a `Content-Length` body, including bodies split across TCP reads.
- Routes GET and POST requests and returns HTTP status lines, headers, and response bodies.
- Validates JSON user creation requests and returns `400` for handled client errors.
- Returns `404` for unknown routes and `405` with an `Allow` header for unsupported methods.
- Uses one thread per connection and a lock around the in-memory user list.
- Limits headers to 16 KiB and request bodies to 1 MiB; client sockets use a five-second timeout.
- Closes the connection after each response.

## Request handling

`main()` accepts connections and starts a thread running `handle_client()`. Each handler parses one request, routes it, and sends the response.

| Stage | Functions | Responsibility |
| --- | --- | --- |
| Read and parse | `read_http_req`, `parse_http_request`, `read_http_body` | Collect headers and body from the TCP stream |
| Route and execute | `route_request`, `api_users` | Validate the route, method, and JSON payload; access shared state |
| Respond | `build_http_response`, `handle_client` | Encode status/headers/body and send the response |

## Run locally

Use Python 3.10 or newer. The server itself uses only the standard library.

```bash
git clone https://github.com/cvrs3d/webserver.git
cd webserver
python3 -m venv .venv
source .venv/bin/activate
python webserver1.py
```

The server listens on `127.0.0.1:8888`. Run the following examples in another terminal.

## API

| Method | Path | Response |
| --- | --- | --- |
| GET | `/` | `200`, plain-text welcome message |
| GET | `/health` | `200`, plain-text `OK` |
| GET | `/users` | `200`, JSON object containing the user list |
| POST | `/users` | `201`, JSON object containing the new user |

```bash
curl -i http://127.0.0.1:8888/health

curl -i -X POST http://127.0.0.1:8888/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alice"}'

curl -i http://127.0.0.1:8888/users
```

The POST response body on a fresh server is:

```json
{"id": 1, "name": "Alice"}
```

`name` must be a string containing at least one non-whitespace character. User IDs are allocated from the in-memory list and restart when the process restarts.

## Tests

With the virtual environment active:

```bash
python -m pip install pytest
python -m pytest -v
```

The tests start their own local socket listeners; a separately running server is not required.

- `test_server.py`: response encoding, routing, and user validation.
- `test_integration.py`: real TCP requests, a fragmented request body, and concurrent creation of 50 users.
- `conftest.py`: isolated user state and ephemeral-port listeners.

## Limitations

- Thread creation is unbounded; there is no worker pool or admission control.
- Keep-alive, chunked transfer encoding, TLS, and complete HTTP validation are not implemented.
- User data is stored only in memory.
- The server is intended for local learning and experiments, not production deployment.
