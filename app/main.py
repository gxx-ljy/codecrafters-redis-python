import socket  # noqa: F401


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment the code below to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    # server_socket = socket.create_server(("localhost", 6379)) # windows

    connection, _ = server_socket.accept()
    while True:
        BUFFER_SIZE_BYTES = 1024
        data = connection.recv(BUFFER_SIZE_BYTES)
        command = data.decode("utf-8")
        print(f"Received command: {command}")

        connection.sendall(b"+PONG\r\n")

    connection.close()

if __name__ == "__main__":
    main()
