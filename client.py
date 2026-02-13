from socket import *
import argparse

# Using last 4 digits of my UMID for the port number
PORT = 9644

# This allows us to pass the server IP when running the program
parser = argparse.ArgumentParser()
parser.add_argument("--ip", default="127.0.0.1")
args = parser.parse_args()

# Create TCP socket
client = socket(AF_INET, SOCK_STREAM)

# Connect to server using provided IP address
client.connect((args.ip, PORT))

# Main loop to keep sending commands
while True:
    # Ask user for a command
    msg = input("Enter command (BUY/SELL/LIST/BALANCE/QUIT/SHUTDOWN): ").strip()

    # If user presses enter with no text, skip it
    if msg == "":
        continue

    # Send the message to the server
    # We add \n because the protocol requires newline at the end
    client.send((msg + "\n").encode())

    # Wait for response from server
    resp = client.recv(4096).decode(errors="replace")

    # Print what the server sent back
    print(resp, end="" if resp.endswith("\n") else "\n")

    # If user typed quit or shutdown, exit client
    if msg.lower() in ("quit", "shutdown"):
        break

# Close the socket when finished
client.close()
