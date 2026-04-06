import socket  # noqa: F401
import threading
import time

db = {}

class RespParser:
    def __init__(self):
        self.buffer = b''
    
    def feed(self, data: bytes):
        """接收新数据，返回所有已解析的完整回复（列表）"""
        self.buffer += data
        replies = []
        while True:
            reply, consumed = self._parse_one(self.buffer)
            if reply is None:   # 数据不完整
                break
            replies.append(reply)
            self.buffer = self.buffer[consumed:]
        return replies
    
    def _parse_one(self, data: bytes):
        """尝试解析一个完整的 RESP 数据类型，返回 (result, consumed_bytes) 或 (None, 0) 表示需要更多数据"""
        if not data:
            return None, 0
        
        # 根据第一个字节分发
        type_byte = data[0]
        if type_byte == ord('+'):
            # 简单字符串：找到 \r\n
            end = data.find(b'\r\n', 1)
            if end == -1:
                return None, 0
            result = data[1:end].decode()
            return result, end + 2
        elif type_byte == ord('-'):
            end = data.find(b'\r\n', 1)
            if end == -1:
                return None, 0
            result = Exception(data[1:end].decode())  # 当作异常抛出
            return result, end + 2
        elif type_byte == ord(':'):
            end = data.find(b'\r\n', 1)
            if end == -1:
                return None, 0
            result = int(data[1:end])
            return result, end + 2
        elif type_byte == ord('$'):
            # 批量字符串
            end = data.find(b'\r\n', 1)
            if end == -1:
                return None, 0
            length = int(data[1:end])
            if length == -1:
                return None, end + 2   # NULL 值
            payload_start = end + 2
            payload_end = payload_start + length
            if len(data) < payload_end + 2:
                return None, 0  # 数据不足
            # 检查结尾 \r\n
            if data[payload_end:payload_end+2] != b'\r\n':
                raise ValueError("Invalid RESP format")
            result = data[payload_start:payload_end]  # 返回 bytes
            return result, payload_end + 2
        elif type_byte == ord('*'):
            end = data.find(b'\r\n', 1)
            if end == -1:
                return None, 0
            count = int(data[1:end])
            if count == -1:
                return None, end + 2
            # 递归解析 count 个元素
            consumed = end + 2
            result = []
            for _ in range(count):
                if consumed >= len(data):
                    return None, 0
                elem, n = self._parse_one(data[consumed:])
                if elem is None and n == 0:  # 数据不完整
                    return None, 0
                result.append(elem)
                consumed += n
            return result, consumed
        else:
            raise ValueError(f"Unknown RESP type byte: {type_byte}")

def encode_resp(obj):
    """将 Python 对象编码为 RESP 字节串"""
    if obj is None:
        return b'$-1\r\n'
    if isinstance(obj, int):
        return f':{obj}\r\n'.encode()
    if isinstance(obj, str):
        data = obj.encode()
        return f'${len(data)}\r\n'.encode() + data + b'\r\n'
    if isinstance(obj, bytes):
        return f'${len(obj)}\r\n'.encode() + obj + b'\r\n'
    if isinstance(obj, (list, tuple)):
        parts = [f'*{len(obj)}\r\n'.encode()]
        for item in obj:
            parts.append(encode_resp(item))
        return b''.join(parts)
    if isinstance(obj, Exception):
        return f'-{obj}\r\n'.encode()
    raise TypeError(f"Unsupported type: {type(obj)}")

def handle_client(conn):
    while True:
        data = conn.recv(1024)
        if not data:
            break

        parser = RespParser()
        commands = parser.feed(data)
        for command in commands:
            if command[0] == b"PING":
                conn.sendall(b"+PONG\r\n")
            elif command == "QUIT":
                conn.close()
                return
            elif command[0] == b"ECHO":
                reply = encode_resp(command[1])
                conn.sendall(reply)
            elif command[0] == b"SET":
                key, value = command[1], command[2]
                # 存储到数据库
                db[key] = value
                # 处理EX和PX
                if len(command) > 3:
                    if command[3] == b"EX":
                        expire_time = int(command[4])
                        threading.Timer(expire_time, db.pop, args=(key,)).start()
                    elif command[3] == b"PX":
                        expire_time = int(command[4]) / 1000
                        threading.Timer(expire_time, db.pop, args=(key,)).start()
                conn.sendall(b"+OK\r\n")
            elif command[0] == b"GET":
                key = command[1]
                # 从数据库中获取值
                value = db.get(key)
                conn.sendall(encode_resp(value))
            elif command[0] == b"RPUSH":
                key, values = command[1], command[2:]
                if key not in db:  # 创建一个空列表
                    db[key] = []
                for value in values:  # 添加多个值
                    db[key].append(value)
                conn.sendall(encode_resp(len(db[key])))
            elif command[0] == b"LPUSH":
                key, values = command[1], command[2:]
                if key not in db:  # 创建一个空列表
                    db[key] = []
                for value in values:  # 添加多个值
                    db[key].insert(0, value)
                conn.sendall(encode_resp(len(db[key])))
            elif command[0] == b"LRANGE":
                key, start, end = command[1], int(command[2]), int(command[3])
                if key not in db:
                    conn.sendall(encode_resp([]))
                else:
                    if start < 0:  # 处理负数索引
                        start = max(0, len(db[key]) + start)
                    if end < 0:  # 处理负数索引
                        end = len(db[key]) + end
                    conn.sendall(encode_resp(db[key][start:end+1]))
            elif command[0] == b"LLEN":
                key = command[1]
                if key not in db:
                    conn.sendall(encode_resp(0))
                else:
                    conn.sendall(encode_resp(len(db[key])))
            elif command[0] == b"LPOP":
                key = command[1]
                if key not in db or not db[key]:
                    conn.sendall(encode_resp(None))
                else:
                    if len(command) > 2:
                        num = int(command[2])
                        value = db[key][:num]
                        db[key] = db[key][num:]
                        conn.sendall(encode_resp(value))
                    else:
                        value = db[key].pop(0)
                        conn.sendall(encode_resp(value))
            elif command[0] == b"BLPOP":
                keys = command[1:-1]  # 获取所有键（除了最后一个参数是超时时间）
                timeout = float(command[-1])  # 超时时间
                
                # 循环检查每个键是否有元素
                for key in keys:
                    if key in db and db[key]:  # 如果键存在且列表不为空
                        value = db[key].pop(0)  # 弹出第一个元素
                        result = [key, value]
                        conn.sendall(encode_resp(result))
                        return
                
                # 如果没有立即可用的元素，设置超时等待
                if timeout == 0:  # 无限期等待
                    while True:
                        # 检查是否有任何键现在有元素
                        found = False
                        for key in keys:
                            if key in db and db[key]:
                                value = db[key].pop(0)
                                result = [key, value]
                                conn.sendall(encode_resp(result))
                                found = True
                                break
                        
                        if found:
                            break
                            
                        # 短暂休眠以避免过度占用CPU
                        time.sleep(0.01)
                else:  # 有限时间等待
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        # 检查是否有任何键现在有元素
                        found = False
                        for key in keys:
                            if key in db and db[key]:
                                value = db[key].pop(0)
                                result = [key, value]
                                conn.sendall(encode_resp(result))
                                found = True
                                break
                        
                        if found:
                            break
                            
                        # 短暂休眠以避免过度占用CPU
                        time.sleep(0.01)
                    
                    # 如果超时仍未找到元素，返回nil
                    if not found:
                        conn.sendall(b"*-1\r\n")
            elif command[0] == b"TYPE":
                key = command[1]
                if key not in db:
                    conn.sendall(b"+none\r\n")
                else:
                    # These types include: string, list, set, zset, hash, stream, and vectorset.
                    if isinstance(db[key], str):
                        conn.sendall(b"+string\r\n")
                    elif isinstance(db[key], list):
                        conn.sendall(b"+list\r\n")
                    elif isinstance(db[key], set):
                        conn.sendall(b"+set\r\n")
                    # elif isinstance(db[key], list):
                    #     conn.sendall(b"+zset\r\n")
                    elif isinstance(db[key], dict):
                        conn.sendall(b"+hash\r\n")
                    # elif isinstance(db[key], list):
                    #     conn.sendall(b"+vectorset\r\n")



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
