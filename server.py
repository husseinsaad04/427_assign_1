from socket import *
import sqlite3

PORT = 9644
BUF = 1024

conn = sqlite3.connect("trading.db")
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS Users (ID INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT, user_name TEXT NOT NULL, password TEXT, usd_balance DOUBLE NOT NULL)")
cur.execute("CREATE TABLE IF NOT EXISTS Stocks (ID INTEGER PRIMARY KEY AUTOINCREMENT, stock_symbol TEXT NOT NULL, stock_name TEXT NOT NULL, stock_balance DOUBLE, user_id INTEGER)")

cur.execute("SELECT COUNT(*) FROM Users")
if cur.fetchone()[0] == 0:
    cur.execute("INSERT INTO Users (first_name,last_name,user_name,password,usd_balance) VALUES ('John','Doe','user1','pass1',100.0)")
    conn.commit()

server = socket(AF_INET, SOCK_STREAM)
server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
server.bind(("", PORT))
server.listen(1)

print("Server running on port", PORT)

while True:
    client, addr = server.accept()
    print("Connected:", addr)

    buffer = ""

    while True:
        data = client.recv(BUF)
        if not data:
            break

        buffer += data.decode(errors="replace")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line == "":
                continue

            print("Received:", line)
            parts = line.split()
            cmd = parts[0].lower()

            if cmd == "balance":
                cur.execute("SELECT first_name,last_name,usd_balance FROM Users WHERE ID=1")
                user = cur.fetchone()
                if not user:
                    client.send("403 message format error\nuser 1 doesn’t exist\n".encode())
                else:
                    client.send(f"200 OK\nBalance for user {user[0]} {user[1]}: ${user[2]:.2f}\n".encode())

            elif cmd == "list":
                cur.execute("SELECT ID,stock_symbol,stock_balance,user_id FROM Stocks WHERE user_id=1 ORDER BY ID")
                rows = cur.fetchall()
                msg = "200 OK\nThe list of records in the Stocks database for user 1:\n"
                if len(rows) == 0:
                    msg += "(no stocks)\n"
                else:
                    for r in rows:
                        msg += f"{r[0]} {r[1]} {r[2]} {r[3]}\n"
                client.send(msg.encode())

            elif cmd == "buy":
                if len(parts) != 5:
                    client.send("403 message format error\nUsage: BUY <SYMBOL> <AMOUNT> <PRICE> <USER_ID>\n".encode())
                    continue

                symbol = parts[1].upper()
                try:
                    amount = float(parts[2])
                    price = float(parts[3])
                    uid = int(parts[4])
                except:
                    client.send("403 message format error\nInvalid BUY parameters\n".encode())
                    continue

                if amount <= 0 or price < 0:
                    client.send("403 message format error\nInvalid BUY parameters\n".encode())
                    continue

                cur.execute("SELECT usd_balance FROM Users WHERE ID=?", (uid,))
                user = cur.fetchone()
                if not user:
                    client.send("403 message format error\nUser not found\n".encode())
                    continue

                total = amount * price
                if user[0] < total:
                    client.send("403 message format error\nNot enough balance\n".encode())
                    continue

                new_usd = user[0] - total
                cur.execute("UPDATE Users SET usd_balance=? WHERE ID=?", (new_usd, uid))

                cur.execute("SELECT stock_balance FROM Stocks WHERE stock_symbol=? AND user_id=?", (symbol, uid))
                stock = cur.fetchone()

                if stock:
                    new_stock = (stock[0] or 0.0) + amount
                    cur.execute("UPDATE Stocks SET stock_balance=? WHERE stock_symbol=? AND user_id=?", (new_stock, symbol, uid))
                else:
                    new_stock = amount
                    cur.execute("INSERT INTO Stocks (stock_symbol,stock_name,stock_balance,user_id) VALUES (?,?,?,?)", (symbol, symbol, amount, uid))

                conn.commit()
                client.send(f"200 OK\nBOUGHT: New balance: {new_stock} {symbol}. USD balance ${new_usd:.2f}\n".encode())

            elif cmd == "sell":
                if len(parts) != 5:
                    client.send("403 message format error\nUsage: SELL <SYMBOL> <AMOUNT> <PRICE> <USER_ID>\n".encode())
                    continue

                symbol = parts[1].upper()
                try:
                    amount = float(parts[2])
                    price = float(parts[3])
                    uid = int(parts[4])
                except:
                    client.send("403 message format error\nInvalid SELL parameters\n".encode())
                    continue

                if amount <= 0 or price < 0:
                    client.send("403 message format error\nInvalid SELL parameters\n".encode())
                    continue

                cur.execute("SELECT stock_balance FROM Stocks WHERE stock_symbol=? AND user_id=?", (symbol, uid))
                stock = cur.fetchone()
                if not stock or (stock[0] or 0.0) < amount:
                    client.send("403 message format error\nNot enough stock balance\n".encode())
                    continue

                new_stock = stock[0] - amount
                cur.execute("UPDATE Stocks SET stock_balance=? WHERE stock_symbol=? AND user_id=?", (new_stock, symbol, uid))

                cur.execute("SELECT usd_balance FROM Users WHERE ID=?", (uid,))
                user = cur.fetchone()
                if not user:
                    client.send("403 message format error\nUser not found\n".encode())
                    conn.commit()
                    continue

                new_usd = user[0] + amount * price
                cur.execute("UPDATE Users SET usd_balance=? WHERE ID=?", (new_usd, uid))

                conn.commit()
                client.send(f"200 OK\nSOLD: New balance: {new_stock} {symbol}. USD ${new_usd:.2f}\n".encode())

            elif cmd == "quit":
                if len(parts) != 1:
                    client.send("403 message format error\nUsage: QUIT\n".encode())
                else:
                    client.send("200 OK\n".encode())
                    client.close()
                    buffer = ""
                    break

            elif cmd == "shutdown":
                if len(parts) != 1:
                    client.send("403 message format error\nUsage: SHUTDOWN\n".encode())
                else:
                    client.send("200 OK\n".encode())
                    client.close()
                    server.close()
                    conn.close()
                    raise SystemExit

            else:
                client.send("400 invalid command\n".encode())

    try:
        client.close()
    except:
        pass
