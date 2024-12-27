import socket
import asyncio
import logging
from contextlib import suppress

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

HOST = "0.0.0.0"
PORT = 8888
REQUEST_BUFFER_SIZE = 1024
REQUEST_TIMEOUT = 5

async def handle_client(client_socket: socket.socket):
    """
    Handle a single client connection.

    1. Read data from the client with a timeout.
    2. Construct and send a simple 'Hello words!' response.
    3. Cleanly close the connection.
    """
    loop = asyncio.get_running_loop()

    try:
        with suppress(asyncio.TimeoutError):
            request_data = await asyncio.wait_for(
                loop.sock_recv(client_socket, REQUEST_BUFFER_SIZE),
                timeout=REQUEST_TIMEOUT
            )

            if not request_data:
                logging.warning("Empty request received.")
                return

            logging.info(f"Received request:\n{request_data.decode('utf-8', errors='replace')}")

        # Construct an HTML response
        response_body = """
        <html>
        <head><title>Hello World!</title></head>
        <body>
            <h1>Ghu is ALIVE!</h1>
            <p>This is an example HTML response from an asyncio server.</p>
        </body>
        </html>
        """

        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{response_body}"
        )


        await loop.sock_sendall(client_socket, response.encode("utf-8"))

    except ConnectionResetError:
        logging.warning("Connection reset by peer.")
    except asyncio.TimeoutError:
        logging.warning("Client connection timed out (no data).")
    except Exception as e:
        logging.error(f"Unexpected error while handling client: {e}", exc_info=True)
    finally:
        client_socket.close()


async def run_server(host=HOST, port=PORT):
    """
    Run the asynchronous server using a manually created socket.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(128)  
    server_socket.setblocking(False)

    logging.info(f"Server is running on http://{host}:{port}")

    loop = asyncio.get_running_loop()

    while True:
        client_socket, client_address = await loop.sock_accept(server_socket)
        logging.info(f"Accepted connection from {client_address}")
        asyncio.create_task(handle_client(client_socket))


def main():
    try:
        asyncio.run(run_server(HOST, PORT))
    except KeyboardInterrupt:
        logging.info("Server shutting down...")


if __name__ == "__main__":
    main()
