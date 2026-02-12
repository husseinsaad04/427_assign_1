from socket import *
import argparse

PORT = 9644

parser = argparse.ArgumentParser()
parser.add_argument("--ip", default="127.0.0.1")
args = parser.parse_args()

client = socket(AF_INET, SOCK_STREAM)
client.connect((args.ip, PORT))

while True:
    msg = input("Enter command (BUY/SELL/LIST/BALANCE/QUIT/SHUTDOWN): ").strip()
    if msg == "":
        continue

    client.send((msg + "\n").encode())
    resp = client.recv(4096).decode(errors="replace")
    print(resp)

    if msg.lower() in ("quit", "shutdown"):
        break

client.close()
