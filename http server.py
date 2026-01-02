"""
HTTP Server
Author: Dor Levek
"""

import socket
import os
import logging
from urllib.parse import urlparse

# Constants and Configuration
IP = '0.0.0.0'
PORT = 80
QUEUE_SIZE = 10
SOCKET_TIMEOUT = 5
WEB_ROOT = "webroot"
DEFAULT_URL = "/index.html"
LOG_FILE = "server.log"

#  Types table
CONTENT_TYPES = {
    "html": "text/html;charset=utf-8",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "css": "text/css",
    "js": "text/javascript; charset=UTF-8",
    "txt": "text/plain",
    "ico": "image/x-icon",
    "gif": "image/jpeg",
    "png": "image/png"
}

REDIRECTION_DICTIONARY = {"/moved": "/"}
FORBIDDEN_LIST = ["/forbidden"]
ERROR_LIST = ["/error"]

logger = logging.getLogger(__name__)


def get_file_data(file_name):
    """
    Reads the content of a file in binary mode.
    """
    try:
        if os.path.isfile(file_name):
            with open(file_name, 'rb') as f:
                return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_name}: {e}")
    return None


def handle_client_request(resource, client_socket):
    """
    Handles GET requests for files and special status codes.
    """
    parsed_url = urlparse(resource)
    uri = parsed_url.path

    # Handle default URI
    if uri == '/':
        uri = DEFAULT_URL

    logger.info(f"GET Request: {uri}")

    # 1. Special Status Codes
    if uri in REDIRECTION_DICTIONARY:
        # 302 Redirect 
        response = f"HTTP/1.1 302 Moved Temporarily\r\nLocation: {REDIRECTION_DICTIONARY[uri]}\r\n\r\n"
        client_socket.send(response.encode())
        return

    if uri in FORBIDDEN_LIST:
        # 403 Forbidden
        client_socket.send(b"HTTP/1.1 403 Forbidden\r\n\r\n")
        return

    if uri in ERROR_LIST:
        # 500 Internal Error
        client_socket.send(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
        return

    # 2. Static File Handling
    file_path = os.path.join(WEB_ROOT, uri.strip("/"))

    if not os.path.isfile(file_path):
        # 404 Not Found
        logger.warning(f"404 Not Found: {file_path}")
        client_socket.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
        return

    # Determine Content Type
    ext = uri.split('.')[-1].lower()
    content_type = CONTENT_TYPES.get(ext, "text/plain")

    data = get_file_data(file_path)
    if data is not None:
        # Build response with headers
        header = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(data)}\r\n\r\n"
        client_socket.send(header.encode() + data)
        logger.info(f"Sent file: {uri} ({len(data)} bytes)")


def handle_client(client_socket):
    """
    Receives data and ensures it's a valid GET request.
    """
    try:
        data = client_socket.recv(4096)
        if not data:
            return

        header_text = data.decode('utf-8', errors='ignore')
        lines = header_text.split('\r\n')
        if not lines:
            return

        request_line = lines[0].split()

        # Validate HTTP GET request structure
        if len(request_line) != 3 or request_line[0] != 'GET' or 'HTTP/1.1' not in request_line[2]:
            # 400 Bad Request
            client_socket.send(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return

        resource = request_line[1]
        handle_client_request(resource, client_socket)

    except Exception as e:
        logger.error(f"Client handling error: {e}")
    finally:
        client_socket.close()


def main():
    """
    Initializes the server socket.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((IP, PORT))
        server_socket.listen(QUEUE_SIZE)
        print(f"Server is running on port {PORT}...")
        logger.info(f"Server started on {IP}:{PORT}")

        while True:
            client_socket, _ = server_socket.accept()
            # Set timeout to handle inactive clients
            client_socket.settimeout(SOCKET_TIMEOUT)
            handle_client(client_socket)
    except Exception as e:
        logger.critical(f"Server crash: {e}")
    finally:
        server_socket.close()


if __name__ == "__main__":
    logging.basicConfig(
        filename=LOG_FILE,
        filemode='w',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Assert
    assert 0 < PORT < 65536, "Port must be valid"
    assert os.path.isdir(WEB_ROOT), f"Error: '{WEB_ROOT}' folder not found"

    main()