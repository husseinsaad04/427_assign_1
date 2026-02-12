from socket import *
import argparse

PORT = 9644

parser = argparse.ArgumentParser()
parser.add_argument("--ip", default="127.0.0.1")
args = parser.parse_args()

client = socket(AF_INET, SOCK_STREAM)
client.connect((args.ip, PORT))

while True:
    msg = input("Enter command (BUY/SELL/LIST/BALANCE/QUIT/SHUTDOWN): ")
    client.send((msg + "\n").encode())
    response = client.recv(4096).decode()
    print(response)

    if msg.lower() == "quit" or msg.lower() == "shutdown":
        break

client.close()
