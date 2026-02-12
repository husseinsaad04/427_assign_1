from socket import *
import argparse

SERVER_PORT = 6969
BUF_SIZE = 1024

def main():
    parser = argparse.ArgumentParser(description="Client for stock trading system")
    parser.add_argument("--ip", default="127.0.0.1", help="IP address of the server")
    args = parser.parse_args()

    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((args.ip, SERVER_PORT))  # <-- MUST be tuple

    try:
        while True:
            user_message = input("Enter command (BUY/SELL/LIST/BALANCE/QUIT/SHUTDOWN): ").strip()
            if not user_message:
                continue

            # protocol expects newline-terminated commands
            client_socket.sendall((user_message + "\n").encode())

            server_response = client_socket.recv(BUF_SIZE).decode(errors="replace")
            print(server_response, end="" if server_response.endswith("\n") else "\n")

            if user_message.upper() in ("QUIT", "SHUTDOWN"):
                break
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
