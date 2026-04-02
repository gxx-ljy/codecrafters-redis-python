import socket  # noqa: F401
import threading

def handle_client(conn):
    while True:
        data = conn.recv(1024)
        command = data.decode("utf-8")
        print(f"Received command: {command}")
        if not data:
            break
        conn.sendall(b"+PONG\r\n")

    conn.close()

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    server_socket = socket.create_server(("localhost", 6379)) # windows

    try:
        while True:
            connection, _ = server_socket.accept()  # wait for client
            threading.Thread(target=handle_client, args=(connection,)).start()
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
