import socket

def test_redis_server():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('localhost', 6379))
        print("Connected to server!")
        
        # 发送 PING 命令 (Redis 协议格式)
        client.send(b'*1\r\n$4\r\nPING\r\n')
        # client.send(b'*2\r\n$4\r\nECHO\r\n$3\r\nhey\r\n')
        response = client.recv(1024)
        print(f"Server response: {response}")
        
        client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_redis_server()