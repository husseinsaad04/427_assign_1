from socket import *
import sqlite3

SERVER_PORT = 9644
BUF_SIZE = 1024
DB_FILE = "trading.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Users table (matches assignment fields closely; email optional in their example schema)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        user_name TEXT NOT NULL,
        password TEXT,
        usd_balance DOUBLE NOT NULL
    );
    """)

    # Stocks table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Stocks (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_symbol VARCHAR(4) NOT NULL,
        stock_name VARCHAR(20) NOT NULL,
        stock_balance DOUBLE,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES Users (ID)
    );
    """)

    # Ensure at least one user exists with $100
    cur.execute("SELECT COUNT(*) FROM Users;")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute("""
            INSERT INTO Users (first_name, last_name, user_name, password, usd_balance)
            VALUES (?, ?, ?, ?, ?);
        """, ("John", "Doe", "user1", "pass1", 100.0))
        conn.commit()

    return conn


def get_user(conn, user_id: int):
    cur = conn.cursor()
    cur.execute("SELECT ID, first_name, last_name, user_name, usd_balance FROM Users WHERE ID = ?;", (user_id,))
    return cur.fetchone()


def get_stock(conn, user_id: int, symbol: str):
    cur = conn.cursor()
    cur.execute("""
        SELECT ID, stock_symbol, stock_name, stock_balance
        FROM Stocks
        WHERE user_id = ? AND UPPER(stock_symbol) = UPPER(?);
    """, (user_id, symbol))
    return cur.fetchone()


def upsert_stock(conn, user_id: int, symbol: str, delta_amount: float):
    # Create if missing; otherwise update balance
    cur = conn.cursor()
    existing = get_stock(conn, user_id, symbol)
    symbol = symbol.upper()

    if existing is None:
        # stock_name not really used by the protocol; store symbol as name for now
        cur.execute("""
            INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id)
            VALUES (?, ?, ?, ?);
        """, (symbol, symbol, max(delta_amount, 0.0), user_id))
        conn.commit()
        return get_stock(conn, user_id, symbol)

    stock_id, _, stock_name, stock_balance = existing
    new_balance = (stock_balance or 0.0) + delta_amount
    if new_balance < -1e-9:
        return None  # indicates failure (not enough stock)

    cur.execute("UPDATE Stocks SET stock_balance = ? WHERE ID = ?;", (new_balance, stock_id))
    conn.commit()
    return get_stock(conn, user_id, symbol)


def update_user_balance(conn, user_id: int, new_balance: float):
    cur = conn.cursor()
    cur.execute("UPDATE Users SET usd_balance = ? WHERE ID = ?;", (new_balance, user_id))
    conn.commit()


def parse_float(x: str):
    try:
        return float(x)
    except ValueError:
        return None


def parse_int(x: str):
    try:
        return int(x)
    except ValueError:
        return None


def handle_command(conn, line: str):
    parts = line.split()
    if not parts:
        return ("403 message format error\n", False, False)

    cmd = parts[0].upper()

    # LIST
    if cmd == "LIST":
        # default to user 1 for now (assignment examples are user 1), but allow LIST <user_id> if you want later
        user_id = 1
        user = get_user(conn, user_id)
        if not user:
            return (f"403 message format error\nuser {user_id} doesn’t exist\n", False, False)

        cur = conn.cursor()
        cur.execute("""
            SELECT ID, stock_symbol, stock_balance, user_id
            FROM Stocks
            WHERE user_id = ?
            ORDER BY ID ASC;
        """, (user_id,))
        rows = cur.fetchall()

        resp = ["200 OK", f"The list of records in the Stocks database for user {user_id}:"]
        if not rows:
            resp.append("(no stocks)")
        else:
            for r in rows:
                sid, sym, bal, uid = r
                resp.append(f"{sid} {sym} {bal} {uid}")
        return ("\n".join(resp) + "\n", False, False)

    # BALANCE
    if cmd == "BALANCE":
        user_id = 1
        user = get_user(conn, user_id)
        if not user:
            return (f"403 message format error\nuser {user_id} doesn’t exist\n", False, False)

        _, first, last, _, usd = user
        return (f"200 OK\nBalance for user {first} {last}: ${usd:.2f}\n", False, False)

    # BUY: BUY SYMBOL AMOUNT PRICE USER_ID
    if cmd == "BUY":
        if len(parts) != 5:
            return ("403 message format error\nUsage: BUY <SYMBOL> <AMOUNT> <PRICE> <USER_ID>\n", False, False)

        symbol = parts[1].upper()
        amount = parse_float(parts[2])
        price = parse_float(parts[3])
        user_id = parse_int(parts[4])

        if amount is None or price is None or user_id is None or amount <= 0 or price < 0:
            return ("403 message format error\nInvalid BUY parameters\n", False, False)

        user = get_user(conn, user_id)
        if not user:
            return (f"403 message format error\nuser {user_id} doesn’t exist\n", False, False)

        _, first, last, _, usd = user
        cost = amount * price
        if usd < cost - 1e-9:
            return ("403 message format error\nNot enough balance\n", False, False)

        new_usd = usd - cost
        update_user_balance(conn, user_id, new_usd)

        stock_row = upsert_stock(conn, user_id, symbol, amount)
        stock_balance = stock_row[3] if stock_row else amount

        msg = (
            "200 OK\n"
            f"BOUGHT: New balance: {stock_balance} {symbol}. USD balance ${new_usd:.2f}\n"
        )
        return (msg, False, False)

    # SELL: SELL SYMBOL AMOUNT PRICE USER_ID
    if cmd == "SELL":
        if len(parts) != 5:
            return ("403 message format error\nUsage: SELL <SYMBOL> <AMOUNT> <PRICE> <USER_ID>\n", False, False)

        symbol = parts[1].upper()
        amount = parse_float(parts[2])
        price = parse_float(parts[3])
        user_id = parse_int(parts[4])

        if amount is None or price is None or user_id is None or amount <= 0 or price < 0:
            return ("403 message format error\nInvalid SELL parameters\n", False, False)

        user = get_user(conn, user_id)
        if not user:
            return (f"403 message format error\nuser {user_id} doesn’t exist\n", False, False)

        stock = get_stock(conn, user_id, symbol)
        if not stock or (stock[3] or 0.0) < amount - 1e-9:
            return ("403 message format error\nNot enough stock balance\n", False, False)

        # deduct stock first
        updated = upsert_stock(conn, user_id, symbol, -amount)
        if updated is None:
            return ("403 message format error\nNot enough stock balance\n", False, False)

        new_stock_balance = updated[3]

        # add USD
        _, first, last, _, usd = user
        gain = amount * price
        new_usd = usd + gain
        update_user_balance(conn, user_id, new_usd)

        msg = (
            "200 OK\n"
            f"SOLD: New balance: {new_stock_balance} {symbol}. USD ${new_usd:.2f}\n"
        )
        return (msg, False, False)

    # QUIT (close client only)
    if cmd == "QUIT":
        if len(parts) != 1:
            return ("403 message format error\nUsage: QUIT\n", False, False)
        return ("200 OK\n", False, True)

    # SHUTDOWN (stop server)
    if cmd == "SHUTDOWN":
        if len(parts) != 1:
            return ("403 message format error\nUsage: SHUTDOWN\n", False, False)
        return ("200 OK\n", True, True)

    return ("400 invalid command\n", False, False)


def main():
    conn = init_db()

    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(("", SERVER_PORT))
    server_socket.listen(1)

    print(f"Server listening on port {SERVER_PORT}...")
    shutting_down = False

    while not shutting_down:
        print("Waiting for client connection...")
        client_socket, client_addr = server_socket.accept()
        print(f"Connection from {client_addr}")

        with client_socket:
            buffer = ""
            while True:
                data = client_socket.recv(BUF_SIZE)
                if not data:
                    break

                buffer += data.decode(errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    print(f"Received: {line}")

                    response, wants_shutdown, close_client = handle_command(conn, line)
                    client_socket.sendall(response.encode())

                    if wants_shutdown:
                        shutting_down = True
                    if close_client or shutting_down:
                        buffer = ""
                        break

                if shutting_down:
                    break

        print("Client session ended.")

    try:
        conn.close()
    except Exception:
        pass
    server_socket.close()
    print("Server shutdown complete.")


if __name__ == "__main__":
    main()
