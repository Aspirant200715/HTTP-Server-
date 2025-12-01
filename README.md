🚀 MiniExpress – A Python HTTP Server From Scratch
A lightweight Express.js-style HTTP framework built using only Python sockets.
.

📌 Overview

This project implements a complete HTTP/1.1 web server from scratch using Python’s standard library only.
No frameworks like Flask, Django, Express, FastAPI, or high-level HTTP libraries were used.

It provides:

Routing (GET, POST, DELETE, etc.)

Query parameters & path parameters

Static file serving

JSON request parsing

In-memory data storage

CORS support

Basic logging middleware

Express.js–style API (app.get(), app.post(), …)

This server is built fully manually using:

socket

threading

json

re
It demonstrates understanding of low-level HTTP, server architecture, and socket programming.

📂 Project Structure
project/
│
├── server.py          # Custom MiniExpress framework (core server)
├── app.py             # Your application routes
├── static/            # Public static files served under /static
│      └── index.html
└── README.md

🧠 How It Works (Beginner Friendly)
1. Sockets

The server manually creates a TCP socket:

socket.socket(socket.AF_INET, socket.SOCK_STREAM)


It binds to:

0.0.0.0:8080


and waits for incoming connections.

2. HTTP Request Parsing

Each incoming HTTP request is manually parsed:

Request line → GET /path HTTP/1.1

Headers → Host, Content-Length, Content-Type, etc.

Body → Parsed for POST/PUT requests

Query parameters → ?message=hello

Path parameters → /user/:id

3. Routing System

You register routes just like Express.js:

@app.get("/echo")
@app.post("/data")
@app.get("/data/:id")


The server internally converts paths like /data/:id into regex and extracts parameters.

4. Threaded Handling

Each request is processed in a separate thread for concurrency.

5. Response Building

Every HTTP response is manually constructed:

HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 27
Access-Control-Allow-Origin: *

🚀 How to Run the Server
1. Install Python 3

Ensure Python 3.8+ is installed.

2. Run the server

In the terminal:

python3 app.py


You will see:

MiniExpress listening on port 8080


Your server is now live at:

👉 http://localhost:8080

🧪 API Endpoints
✔ GET /

Returns welcome message

Request

GET /


Response

Welcome to MiniExpress!

✔ GET /echo?message=hello

Echoes the query param.

Response

Echo: hello

✔ GET /user/:id

Example:

GET /user/10


Response:

{"user_id": "10"}

✔ POST /data

Stores JSON in memory.

Example Request

POST /data
Content-Type: application/json

{"name":"Soham","value":123}


Response

{"id": 1}

✔ GET /data

Returns all records.

[
  {"id":1,"data":{"name":"Soham","value":123}}
]

✔ GET /data/:id
GET /data/1


Response

{"id": 1, "data": {"name":"Soham","value":123}}


If not found → 404 Not Found

📁 Static File Serving

Any file placed in:

./static


is served from URL:

/static/<filename>


Example:

static/index.html → http://localhost:8080/static/index.html

🛠 Bonus Features Implemented
✔ 1. Request Logging Middleware

Every request prints:

('127.0.0.1', 42022) - GET /data

✔ 2. Static File Serving

Automatically serves files under /static.

✔ 3. CORS Support

All responses include:

Access-Control-Allow-Origin: *

🧱 Design Decisions
Why build from scratch?

To understand:

How browsers communicate with servers

How HTTP requests look before frameworks parse them

How routing works internally

How to build low-level I/O logic

How modern frameworks (Express/Flask/FastAPI) work internally

Why threading?

The assignment needs ability to handle many simultaneous connections.

Why in-memory storage?

Meet the requirement: “store data in RAM”

Regex-based routing

Used to support:

/user/:id
/data/:id

🧪 Test Using cURL
Home:
curl http://localhost:8080/

Echo:
curl "http://localhost:8080/echo?message=hello"

POST data:
curl -X POST http://localhost:8080/data \
-H "Content-Type: application/json" \
-d '{"name":"Soham","value":123}'

GET all data:
curl http://localhost:8080/data

📌 Limitations
Data is not persistent (RAM only)

No HTTPS support

Single-thread performance may vary

No authentication (can be added)

os

It demonstrates understanding of low-level HTTP, server architecture, and socket programming.
