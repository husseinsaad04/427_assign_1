from socket import *

SERVER_PORT = 6969
BUF_SIZE = 1024

def handle_command(line: str):
    # line is already stripped (no newline)
    parts = line.split()
    if not parts:
        return ("403 message format error\n", False)

    cmd = parts[0].upper()

    if cmd == "LIST":
        # placeholder response
        return ("200 OK\n(No records yet)\n", False)

    if cmd == "BALANCE":
        # placeholder response
        return ("200 OK\nBalance for user: $100.00\n", False)

    if cmd == "BUY":
        # Expected: BUY SYMBOL AMOUNT PRICE USER_ID
        if len(parts) != 5:
            return ("403 message format error\nUsage: BUY <SYMBOL> <AMOUNT> <PRICE> <USER_ID>\n", False)
        return ("200 OK\nBOUGHT: (placeholder)\n", False)

    if cmd == "SELL":
        # Expected: SELL SYMBOL AMOUNT PRICE USER_ID
        if len(parts) != 5:
            return ("403 message format error\nUsage: SELL <SYMBOL> <AMOUNT> <PRICE> <USER_ID>\n", False)
        return ("200 OK\nSOLD: (placeholder)\n", False)

    if cmd == "QUIT":
        return ("200 OK\n", False)  # close client connection only

    if cmd == "SHUTDOWN":
        return ("200 OK\n", True)   # shut server down

    return ("400 invalid command\n", False)


def main():
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(("", SERVER_PORT))
    server_socket.listen(1)

    shutting_down = False
    print(f"Server listening on port {SERVER_PORT}...")

    while not shutting_down:
        print("Waiting for client connection...")
        client_socket, client_addr = server_socket.accept()
        print(f"Connection from {client_addr}")

        # handle exactly one client at a time; when they quit, accept next
        with client_socket:
            buffer = ""
            while True:
                data = client_socket.recv(BUF_SIZE)
                if not data:
                    # client disconnected
                    break

                buffer += data.decode(errors="replace")

                # process full lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    print(f"Received: {line}")

                    response, wants_shutdown = handle_command(line)
                    client_socket.sendall(response.encode())

                    if line.upper().startswith("QUIT"):
                        # close only this client's session
                        buffer = ""
                        break

                    if wants_shutdown:
                        shutting_down = True
                        buffer = ""
                        break

                if shutting_down:
                    break

        print("Client session ended.")

    server_socket.close()
    print("Server shutdown complete.")


if __name__ == "__main__":
    main()
