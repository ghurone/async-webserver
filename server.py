import asyncio
import logging
import os
import socket
from contextlib import suppress

logging.basicConfig(
    level=logging.INFO,
    format="| %(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)


class GhuServer:
    HTTP_STATUS = {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    }

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8888,
        request_buffer_size: int = 1024,
        template_folder: str = "templates",
        request_timeout: int = 5,
    ) -> None:
        self.host = host
        self.port = port
        self.request_buffer_size = request_buffer_size
        self.request_timeout = request_timeout
        self.template_folder = template_folder
        self.routes = {}

    def route(self, path: str):
        """
        Decorator para registrar uma função como handler de uma rota específica.
        """
        def decorator(func):
            self.routes[path] = func
            return func

        return decorator

    def render_template(self, template_name: str) -> str:
        """
        Carrega um arquivo HTML da pasta 'templates' e retorna seu conteúdo.
        """
        template_path = os.path.join(self.template_folder, template_name)
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template não encontrado: '{template_name}'")

    def _build_response(
        self, status_code: int, body: str, content_type: str = "text/html; charset=utf-8"
    ) -> str:
        """
        Constrói a string de resposta HTTP incluindo status, cabeçalhos e corpo.
        """
        status_text = self.HTTP_STATUS.get(status_code, "Unknown")
        response_status = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response_headers = (
            f"{response_status}"
            f"Content-Type: {content_type}\r\n"
            f"Connection: close\r\n"
            "\r\n"
        )
        return response_headers + body

    async def handle_client(self, client_socket: socket.socket) -> None:
        """
        Processa a conexão de um cliente: lê a rota solicitada, chama o handler
        correspondente e envia a resposta.
        """
        loop = asyncio.get_running_loop()

        try:
            with suppress(asyncio.TimeoutError):
                request_data = await asyncio.wait_for(
                    loop.sock_recv(client_socket, self.request_buffer_size),
                    timeout=self.request_timeout
                )

            if not request_data:
                logging.warning("Recebida uma requisição vazia.")
                return

            request_text = request_data.decode("utf-8", errors="replace")
            logging.info(f"Request:\n{request_text}")

            request_line = request_text.split("\r\n")[0]
            parts = request_line.split(" ")
            if len(parts) < 2:
                response = self._build_response(400, "<h1>400 Bad Request</h1>")
            else:
                method, path = parts[0], parts[1]
                route_handler = self.routes.get(path)
                if route_handler is None:
                    response = self._build_response(404, "<h1>404 Not Found</h1>")
                else:
                    try:
                        body = route_handler()
                        if body is None:
                            response = self._build_response(404, "<h1>404 Not Found</h1>")
                        else:
                            response = self._build_response(200, body)
                    except Exception as e:
                        logging.error(f"Erro na rota '{path}': {e}", exc_info=True)
                        response = self._build_response(500, "<h1>500 Internal Server Error</h1>")

            await loop.sock_sendall(client_socket, response.encode("utf-8"))

        except ConnectionResetError:
            logging.warning("Conexão resetada pelo cliente.")
        except asyncio.TimeoutError:
            logging.warning("Tempo limite da conexão excedido (sem dados).")
        except Exception as e:
            logging.error(f"Erro inesperado ao lidar com o cliente: {e}", exc_info=True)
        finally:
            client_socket.close()

    async def run_server(self) -> None:
        """
        Cria o socket e aguarda conexões de forma assíncrona.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(128)
        server_socket.setblocking(False)

        logging.info(f"Servidor rodando em http://{self.host}:{self.port}")
        loop = asyncio.get_running_loop()

        while True:
            client_socket, client_address = await loop.sock_accept(server_socket)
            logging.info(f"Conexão aceita de {client_address}")
            asyncio.create_task(self.handle_client(client_socket))

    def run(self) -> None:
        """
        Executa o loop de eventos do asyncio até ser interrompido.
        """
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            logging.info("Servidor encerrando...")



if __name__ == "__main__":
    server = GhuServer(host="0.0.0.0", port=8888)

    @server.route("/")
    def index() -> str:
        return server.render_template("index.html")

    @server.route("/hello")
    def hello() -> str:
        return "<h1>Hello World!</h1><p>HEHEHE It's works!!!</p>"

    server.run()
