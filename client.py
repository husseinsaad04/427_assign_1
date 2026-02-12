from socket import *
import argparse

SERVER_PORT = 9644
BUF_SIZE = 4096

def main():
    parser = argparse.ArgumentParser(description="Client for stock trading system")
    parser.add_argument("--ip", default="127.0.0.1", help="IP address of the server")
    args = parser.parse_args()

    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((args.ip, SERVER_PORT))

    try:
        while True:
            msg = input("Enter command (BUY/SELL/LIST/BALANCE/QUIT/SHUTDOWN): ").strip()
            if not msg:
                continue

            client_socket.sendall((msg + "\n").encode())
            resp = client_socket.recv(BUF_SIZE).decode(errors="replace")
            print(resp, end="" if resp.endswith("\n") else "\n")

            if msg.upper() in ("QUIT", "SHUTDOWN"):
                break
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
