# Simple WebServer

## Overview

This test mini-project is made to work with socket library and better understand how TCP and HTTP work.

## Features

- HTTP/1.1 request parsing using Python sockets
- Dynamic HTTP response generation with status codes and headers
- URL routing with GET and POST methods
- JSON serialization and deserialization
- Request validation and error handling
- Concurrent client handling using Python threads
- Thread-safe in-memory user storage using `threading.Lock`
- Unit, integration, and concurrency tests with pytest

## Architecture 

TCP Client
    |
    v
main() → socket.accept()
    |
    v
threading.Thread()
    |
    v
handle_client()
    |
    v
read_http_req()
    |
    v
parse_http_request()
    |
    +--> read_http_body()
    |
    v
route_request()
    |
    +--> api_users()
    |
    v
build_http_response()
    |
    v
socket.sendall()
    |
    v
TCP Client

## API Endpoints

| Method | Endpoint | Description | Status |
|---|---|---|---:|
| GET | `/` | Welcome message | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/users` | Retrieve all users | 200 |
| POST | `/users` | Create a user | 201 |

## POST Example 
Request:
```bash
curl -X POST http://127.0.0.1:8888/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}'
```
Respponse:
```bash
{"id": 1, "name": "Alice"}
```


## Getting Started 

# Clone repository
git clone <repository-url>
cd web-server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Run server
python webserver1.py

## Testing 

```bash
python -m pytest -v
python -m pytest --collect-only -q 
```

## Limitations

- Thread-per-connection architecture has no limit on the number of concurrent threads.
- HTTP/1.1 support is partial; persistent connections and chunked transfer encoding are not implemented.
- User data is stored in memory without persistence.
- The server is intended for educational purposes, not production deployment.