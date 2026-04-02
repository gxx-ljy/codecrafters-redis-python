# Socket 完全指南

## 一、Socket 是什么？

**Socket 是操作系统提供的一种进程间通信（IPC）机制**，允许不同计算机上的进程通过网络交换数据。

从技术角度说：
- **它是一个编程接口**（API），程序通过它来使用网络功能
- **它是一个文件描述符**（Unix/Linux 下一切皆文件），可以用 `read()`、`write()` 来操作
- **它是一个通信端点**，由 `IP地址 + 端口号` 唯一标识

---

## 二、Socket 的历史

| 时间 | 事件 |
|------|------|
| 1982 | BSD Unix 4.2 引入 socket 接口 |
| 1983 | 成为 BSD Unix 标准组件 |
| 1990s | 移植到 System V、Windows（Winsock） |
| 至今 | 所有主流操作系统的网络编程标准 |

名字 "socket" 来源于电话接线板上的"插孔"比喻——插入就能通信。

---

## 三、Socket 的类型

### 按协议分

| 类型 | 协议 | 特点 | 适用场景 |
|------|------|------|----------|
| **SOCK_STREAM** | TCP | 可靠、有序、有连接、有流量控制 | HTTP、FTP、SSH、数据库 |
| **SOCK_DGRAM** | UDP | 不可靠、无序、无连接、低延迟 | DNS、视频流、VoIP、游戏 |
| **SOCK_RAW** | IP | 绕过传输层，直接操作 IP 包 | ping（ICMP）、嗅探器、防火墙 |
| **SOCK_SEQPACKET** | SCTP | 可靠、有序、有边界、多流 | 电信信令 |

### 按地址族分

| 地址族 | 说明 |
|--------|------|
| **AF_INET** | IPv4 网络通信 |
| **AF_INET6** | IPv6 网络通信 |
| **AF_UNIX** | 同一台机器的进程间通信（使用文件系统路径） |
| **AF_BLUETOOTH** | 蓝牙通信 |

---

## 四、Socket 的完整生命周期

### TCP Socket（面向连接）

```
服务端                               客户端
   │                                   │
   │  socket() 创建socket               │  socket() 创建socket
   │                                   │
   │  bind() 绑定地址和端口              │
   │                                   │
   │  listen() 开始监听                 │
   │                                   │
   │  accept() 阻塞等待          ─────►│  connect() 发起连接
   │                                   │  （TCP三次握手）
   │  accept() 返回新的socket           │
   │                                   │
   │  read()/write() 收发数据 ◄───────►│  write()/read() 收发数据
   │                                   │
   │  close() 关闭连接                  │  close() 关闭连接
   │                                   │  （TCP四次挥手）
```

### UDP Socket（无连接）

```
服务端                               客户端
   │                                   │
   │  socket() 创建socket               │  socket() 创建socket
   │                                   │
   │  bind() 绑定地址和端口              │
   │                                   │
   │  recvfrom() 阻塞等待       ◄───────│  sendto() 直接发送（无连接）
   │                                   │
   │  sendto() 回复           ────────►│  recvfrom() 接收
   │                                   │
   │  无需close，直接退出               │  无需close，直接退出
```

---

## 五、每个函数的详细解释

### 1. `socket()` — 创建套接字

```c
int socket(int domain, int type, int protocol);
```

- `domain`：地址族（AF_INET、AF_INET6、AF_UNIX）
- `type`：套接字类型（SOCK_STREAM、SOCK_DGRAM）
- `protocol`：协议（通常设0，系统自动选择）

返回值是一个**文件描述符**（整数），用于后续所有操作。

### 2. `bind()` — 绑定地址

```c
int bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
```

- 把 socket 和特定的 IP+端口 关联起来
- 服务端必须 bind，客户端通常不用（系统自动分配临时端口）

### 3. `listen()` — 开始监听

```c
int listen(int sockfd, int backlog);
```

- 把 socket 变成被动（监听）模式
- `backlog`：等待连接队列的最大长度

### 4. `accept()` — 接受连接

```c
int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen);
```

- **阻塞**直到有客户端连接
- 返回一个**新的 socket** 用于和客户端通信
- 原来的 socket 继续用于监听新连接

### 5. `connect()` — 发起连接

```c
int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
```

- 客户端调用，连接到服务器
- 对于 TCP，会触发三次握手

### 6. `send()` / `recv()` — 收发数据

```c
ssize_t send(int sockfd, const void *buf, size_t len, int flags);
ssize_t recv(int sockfd, void *buf, size_t len, int flags);
```

- TCP 专用
- 可能一次发不完/收不完，需要循环

### 7. `sendto()` / `recvfrom()` — 收发数据（UDP）

```c
ssize_t sendto(int sockfd, const void *buf, size_t len, int flags,
               const struct sockaddr *dest_addr, socklen_t addrlen);
```

- UDP 专用，每个包都指定目标地址
- 无连接，直接发送

### 8. `close()` — 关闭连接

```c
int close(int fd);
```

- 关闭 socket，释放资源
- TCP 会发送 FIN 包开始四次挥手

---

## 六、核心数据结构

### `struct sockaddr`

通用的 socket 地址结构（所有具体地址的父类）：

```c
struct sockaddr {
    sa_family_t sa_family;  // 地址族
    char sa_data[14];       // 地址数据
};
```

### `struct sockaddr_in`（IPv4 实际使用的结构）

```c
struct sockaddr_in {
    sa_family_t    sin_family;   // AF_INET
    in_port_t      sin_port;     // 端口号（网络字节序）
    struct in_addr sin_addr;     // IPv4 地址
    char           sin_zero[8];  // 填充，保持与sockaddr大小相同
};
```

### `struct sockaddr_in6`（IPv6）

```c
struct sockaddr_in6 {
    sa_family_t     sin6_family;   // AF_INET6
    in_port_t       sin6_port;     // 端口号
    uint32_t        sin6_flowinfo; // 流信息
    struct in6_addr sin6_addr;     // IPv6 地址
    uint32_t        sin6_scope_id; // 范围ID
};
```

### `struct addrinfo`（现代编程用）

```c
struct addrinfo {
    int              ai_flags;
    int              ai_family;     // AF_INET 或 AF_INET6
    int              ai_socktype;   // SOCK_STREAM 或 SOCK_DGRAM
    int              ai_protocol;
    size_t           ai_addrlen;
    struct sockaddr *ai_addr;       // 实际地址结构
    char            *ai_canonname;
    struct addrinfo *ai_next;       // 链表，支持多个结果
};
```

---

## 七、重要的技术细节

### 1. 字节序（大端/小端）

网络协议规定使用**大端字节序**（网络字节序）。

```c
// 主机字节序 ←→ 网络字节序 转换函数
uint16_t htons(uint16_t hostshort);   // host to network short
uint32_t htonl(uint32_t hostlong);    // host to network long
uint16_t ntohs(uint16_t netshort);    // network to host short
uint32_t ntohl(uint32_t netlong);     // network to host long
```

### 2. 端口号范围

| 范围 | 类型 | 说明 |
|------|------|------|
| 0-1023 | 系统端口（Well-known） | 需要 root/admin 权限 |
| 1024-49151 | 注册端口（Registered） | 普通用户可用 |
| 49152-65535 | 动态/私有端口（Ephemeral） | 临时分配给客户端 |

### 3. 阻塞 vs 非阻塞

**阻塞模式（默认）**：
- `accept()`、`recv()`、`send()` 会一直等待
- 简单，但一个线程只能处理一个连接

**非阻塞模式**：
```c
// 设置非阻塞
int flags = fcntl(sockfd, F_GETFL, 0);
fcntl(sockfd, F_SETFL, flags | O_NONBLOCK);
```

### 4. 网络 I/O 模型

| 模型 | 说明 |
|------|------|
| 阻塞 I/O | 最简单，但并发能力差 |
| 非阻塞 I/O + 轮询 | CPU 空转浪费 |
| I/O 多路复用（select/poll/epoll/kqueue） | 一个线程监视多个连接 |
| 信号驱动 I/O | 内核通知数据到达 |
| 异步 I/O | 内核完成整个操作再通知 |

---

## 八、常用系统限制

```bash
# 查看最大文件描述符数
ulimit -n

# 查看端口范围
cat /proc/sys/net/ipv4/ip_local_port_range

# 查看 TIME_WAIT 相关参数
cat /proc/sys/net/ipv4/tcp_tw_reuse
cat /proc/sys/net/ipv4/tcp_tw_recycle
```

---

## 九、常见问题和陷阱

| 问题 | 原因 | 解决 |
|------|------|------|
| `Address already in use` | 端口被占用或 TIME_WAIT | 用 `setsockopt(SO_REUSEADDR)` |
| `Connection refused` | 目标端口没有服务监听 | 检查服务是否启动 |
| `Connection reset` | 对方异常关闭 | 代码逻辑错误 |
| 数据粘包 | TCP 是流式，无边界 | 应用层定义消息边界 |
| 信号中断 | `EINTR` 错误 | 循环重试 |
| 部分发送/接收 | 不一定一次发完 | 循环直到完成 |

---

## 十、Python 中的 socket（补充）

Python 的 `socket` 模块是对底层 C API 的封装：

```python
import socket

# 创建 TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 设置地址重用
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 绑定
sock.bind(('0.0.0.0', 6379))

# 监听
sock.listen(5)

# 接受连接（返回新的 socket 和地址）
conn, addr = sock.accept()

# 接收数据（阻塞，最多1024字节）
data = conn.recv(1024)

# 发送数据
conn.sendall(b'+PONG\r\n')  # sendall 保证全部发送

# 关闭
conn.close()
```

Python 的 `socket.create_server()` 是更高级的封装：

```python
# 等价于上面的 bind + listen
server = socket.create_server(('localhost', 6379), reuse_port=True)
```

---

## 十一、总结

Socket 是网络编程的基石，理解它需要掌握：

1. **类型**：TCP vs UDP，面向连接 vs 无连接
2. **生命周期**：socket → bind/listen → accept/connect → send/recv → close
3. **核心概念**：文件描述符、字节序、阻塞/非阻塞
4. **实践陷阱**：地址重用、粘包、信号中断、部分读写

