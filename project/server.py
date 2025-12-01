import socket
import threading
import re
import json
import urllib.parse
import mimetypes
import os

# ---------------------------------------------------------
# REQUEST OBJECT
# ---------------------------------------------------------
# This class stores everything about the incoming request:
# - method (GET, POST, DELETE, etc.)
# - path (/data, /echo?message=hi)
# - headers (Content-Type, Host, etc.)
# - body (JSON or text)
# - query parameters (?message=hi)
# - path parameters (/user/:id)
# ---------------------------------------------------------

class Request:
    def __init__(self, method, path, headers, body, client_addr):
        self.method = method
        self.raw_path = path  # full path including query string

        # Split path into "actual path" + "query string"
        if '?' in path:
            path_only, query_string = path.split('?', 1)
        else:
            path_only, query_string = path, ''
        self.path = path_only

        # Parse query parameters into a dictionary
        # Example: /echo?message=hello → {"message": "hello"}
        self.query = {}
        if query_string:
            parsed_qs = urllib.parse.parse_qs(query_string)
            for key, values in parsed_qs.items():
                self.query[key] = values[0] if len(values) == 1 else values

        self.headers = headers     # incoming headers
        self.params = {}           # path parameters will be stored here
        self.client_addr = client_addr

        # Parse request body depending on Content-Type
        self.body = None
        if body:
            content_type = headers.get('Content-Type', '')

            # If body is JSON → decode JSON
            if 'application/json' in content_type:
                try:
                    self.body = json.loads(body)
                except:
                    # If JSON is invalid, store raw data
                    self.body = body.decode('utf-8', errors='ignore')

            # If body is form-data style (x-www-form-urlencoded)
            elif 'application/x-www-form-urlencoded' in content_type:
                body_str = body.decode('utf-8', errors='ignore')
                self.body = urllib.parse.parse_qs(body_str)

            # Otherwise, store raw body
            else:
                self.body = body


# ---------------------------------------------------------
# RESPONSE OBJECT
# ---------------------------------------------------------
# This builds the HTTP response sent back to the client.
# It includes:
# - status line (HTTP/1.1 200 OK)
# - headers (Content-Length, Content-Type...)
# - body
# ---------------------------------------------------------

class Response:
    def __init__(self, client_sock):
        self.client_sock = client_sock
        self.status_code = 200
        self.status_text = 'OK'
        self.headers = {}
        self.sent = False

    # Set the HTTP status code
    def status(self, code):
        self.status_code = code
        self.status_text = {
            200: 'OK', 201: 'Created', 202: 'Accepted', 204: 'No Content',
            301: 'Moved Permanently', 302: 'Found', 400: 'Bad Request',
            401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
            500: 'Internal Server Error'
        }.get(code, '')
        return self

    # Add a header
    def set_header(self, name, value):
        self.headers[name] = value

    # Send response (text or bytes)
    def send(self, data):
        if self.sent:
            return

        # Convert different types of data into bytes
        if data is None:
            body_bytes = b''
        elif isinstance(data, (bytes, bytearray)):
            body_bytes = data
        else:
            body_bytes = str(data).encode('utf-8')

        # Default headers
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'text/plain; charset=utf-8'

        # Add CORS (allow all origins)
        if 'Access-Control-Allow-Origin' not in self.headers:
            self.headers['Access-Control-Allow-Origin'] = '*'

        # Always close connection after response
        self.headers['Connection'] = 'close'
        self.headers['Content-Length'] = str(len(body_bytes))

        # Build HTTP response text
        status_line = f"HTTP/1.1 {self.status_code} {self.status_text}\r\n"

        # Send status line, headers, and body
        try:
            self.client_sock.sendall(status_line.encode('utf-8'))

            for name, value in self.headers.items():
                header_line = f"{name}: {value}\r\n"
                self.client_sock.sendall(header_line.encode('utf-8'))

            self.client_sock.sendall(b"\r\n")  # end of headers

            if body_bytes:
                self.client_sock.sendall(body_bytes)

        except BrokenPipeError:
            pass
        finally:
            self.sent = True

    # Send JSON response
    def json(self, obj):
        try:
            body = json.dumps(obj)
        except:
            body = str(obj)
        self.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.send(body)


# ---------------------------------------------------------
# MINIEXPRESS FRAMEWORK
# ---------------------------------------------------------
# This class is the HEART of your entire server.
# It handles:
# - registering routes
# - pattern matching (/user/:id)
# - serving static files
# - parsing requests
# - calling correct handler
# - sending responses
# ---------------------------------------------------------

class MiniExpress:
    def __init__(self):
        self.routes = {}          # store all GET/POST routes
        self.static_routes = []   # store static file mappings
        self.server_socket = None

    # Convert route string into regex
    # Example: /user/:id  ->  ^/user/(?P<id>[^/]+)$
    def add_route(self, method, path, handler):
        if path == '/':
            pattern = '^/$'
        else:
            pattern = '^'
            parts = path.strip('/').split('/')
            for part in parts:
                # Path param
                if part.startswith(':'):
                    name = part[1:]
                    pattern += f"/(?P<{name}>[^/]+)"
                else:
                    pattern += f"/{re.escape(part)}"
            pattern += '/?$'

        regex = re.compile(pattern)
        self.routes.setdefault(method, []).append((regex, handler))

    # Decorators for route registration (Express style)
    def get(self, path):
        def decorator(func):
            self.add_route('GET', path, func)
            return func
        return decorator

    def post(self, path):
        def decorator(func):
            self.add_route('POST', path, func)
            return func
        return decorator

    def delete(self, path):
        def decorator(func):
            self.add_route('DELETE', path, func)
            return func
        return decorator

    def put(self, path):
        def decorator(func):
            self.add_route('PUT', path, func)
            return func
        return decorator

    def patch(self, path):
        def decorator(func):
            self.add_route('PATCH', path, func)
            return func
        return decorator

    # Map a folder to a URL path
    def use_static(self, prefix, directory):
        if not prefix.startswith('/'):
            prefix = '/' + prefix
        prefix = prefix.rstrip('/')
        self.static_routes.append((prefix, directory))


    # -----------------------------------------------------
    # Handle each incoming HTTP request
    # -----------------------------------------------------
    def handle_request(self, client_sock, client_addr):
        rfile = client_sock.makefile('rb')

        # First line of HTTP request → "GET /home HTTP/1.1"
        try:
            line = rfile.readline().decode('utf-8')
        except:
            client_sock.close()
            return

        if not line:
            client_sock.close()
            return

        parts = line.strip().split()
        if len(parts) != 3:
            client_sock.close()
            return

        method, raw_path, version = parts

        # Read headers
        headers = {}
        while True:
            hline = rfile.readline().decode('utf-8')
            if not hline or hline in ('\r\n', '\n'):
                break
            if ':' in hline:
                name, val = hline.split(':', 1)
                headers[name.strip()] = val.strip()

        # Read request body
        body = b''
        if 'Content-Length' in headers:
            length = int(headers['Content-Length'])
            body = rfile.read(length)

        # Create Request and Response objects
        req = Request(method, raw_path, headers, body, client_addr)
        res = Response(client_sock)

        print(f"{client_addr} - {method} {req.raw_path}")  # logging middleware

        # Handle CORS preflight
        if method == 'OPTIONS':
            res.status(200)
            res.headers['Access-Control-Allow-Origin'] = '*'
            res.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
            res.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            res.send('')
            client_sock.close()
            return

        # -------------------------------------------------
        # Static file serving logic
        # -------------------------------------------------
        served = False
        for prefix, directory in self.static_routes:
            if req.path.startswith(prefix):
                rel_path = req.path[len(prefix):]
                file_path = os.path.join(directory, rel_path.lstrip('/'))

                # If folder, serve index.html
                if os.path.isdir(file_path):
                    file_path = os.path.join(file_path, 'index.html')

                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    ctype, _ = mimetypes.guess_type(file_path)
                    res.headers['Content-Type'] = ctype or 'application/octet-stream'
                    res.send(content)
                    served = True
                except FileNotFoundError:
                    pass
                except Exception as e:
                    res.status(500).send(f"Error reading static file: {e}")
                    served = True
                break

        if served:
            client_sock.close()
            return

        # -------------------------------------------------
        # Route matching using regex
        # -------------------------------------------------
        route_list = self.routes.get(method, [])
        for regex, handler in route_list:
            match = regex.match(req.path)
            if match:
                req.params = match.groupdict()
                try:
                    handler(req, res)  # call user route handler
                except Exception as e:
                    print(f"Handler error for {req.path}: {e}")
                    res.status(500).send("Internal Server Error")
                finally:
                    if not res.sent:
                        res.send(None)
                client_sock.close()
                return

        # If no route matched
        res.status(404).send("Not Found")
        client_sock.close()


    # -----------------------------------------------------
    # Start the server (threaded)
    # -----------------------------------------------------
    def listen(self, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('', port))
        self.server_socket.listen(5)

        print(f"MiniExpress listening on port {port}")

        try:
            # Accept clients forever (each client → new thread)
            while True:
                client_sock, client_addr = self.server_socket.accept()
                thread = threading.Thread(
                    target=self.handle_request,
                    args=(client_sock, client_addr)
                )
                thread.daemon = True
                thread.start()

        except KeyboardInterrupt:
            print("Server shutting down.")
        finally:
            self.server_socket.close()
