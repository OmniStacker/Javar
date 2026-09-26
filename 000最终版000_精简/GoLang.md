# GoLang知识汇总

## 一、进阶网络通信

### 1. 标准库 net 包

Go 标准库的 `net` 包支持基于 IP 层、TCP/UDP 层及更高层（HTTP、FTP、SMTP）的网络操作，其中用于 IP 层的称为 Raw Socket。

关键函数：
- `net.Listen()`：服务端监听
- `net.Dial()`：客户端发起连接

**服务端**

```go
package main

import (
    "fmt"
    "net"
)

func main() {
    fmt.Printf("服务器准备开启。。。。")
    listener, err := net.Listen("tcp", "127.0.0.1:8081")
    if err != nil {
        fmt.Println(err)
        return
    }
    defer listener.Close()
    for {
        conn, err := listener.Accept()
        if err != nil {
            fmt.Println(err)
            return
        } else {
            fmt.Println(conn)
        }
    }
}
```

**客户端**

```go
package main

import (
    "fmt"
    "net"
)

func main() {
    fmt.Printf("客户端准备开启。。。。")
    conn, err := net.Dial("tcp", "192.168.49.1:8081")
    if err != nil {
        fmt.Println(err)
    }
    defer conn.Close()
    fmt.Println("客户端连接成功", conn.RemoteAddr().String())
}
```

**客户端通过标准流发送数据**：关键方法 `os.Stdin`、`bufio`、`conn.Write`、`conn.Read`。

```go
func main() {
    fmt.Printf("客户端准备开启。。。。")
    conn, err := net.Dial("tcp", "192.168.49.1:8081")
    if err != nil {
        fmt.Println(err)
    }
    go proc(conn)
}

func proc(conn net.Conn) {
    defer conn.Close()
    reader := bufio.NewReader(os.Stdin)  // 标准输入流
    line, err := reader.ReadString('\n') // 每次读一行
    if err != nil {
        fmt.Println(err)
    }
    len, err := conn.Write([]byte(line))
    if err != nil {
        fmt.Println(err)
    }
    fmt.Println("客户端连接成功", conn.RemoteAddr().String(), "并且写了", len, "个字节")
}
```

**服务端读取数据**

```go
func main() {
    fmt.Printf("服务器准备开启。。。。")
    listener, err := net.Listen("tcp", "0.0.0.0:8081")
    if err != nil {
        fmt.Println(err)
        return
    }
    defer listener.Close()
    for {
        conn, err := listener.Accept()
        go proc(conn)
        if err != nil {
            fmt.Println(err) // err = EOF，客户端退出了
            return
        } else {
            fmt.Println(conn.LocalAddr())
        }
    }
}

func proc(conn net.Conn) {
    defer conn.Close()
    for {
        buf := make([]byte, 1024)
        n, err := conn.Read(buf) // 返回接收的字节数
        if err != nil {
            fmt.Println(err)
            return
        }
        fmt.Println(n)
        fmt.Println(string(buf[:n]))
    }
}
```

### 2. HTTP 服务与模板引擎

```go
func main() {
    handle1 := handle1{}
    http.Handle("/handler1", &handle1)
    s := http.Server{
        Addr:    "127.0.0.1:8081",
        Handler: nil,
    }
    s.ListenAndServe()
}

type handle1 struct{}

func (h *handle1) ServeHTTP(w http.ResponseWriter, req *http.Request) {
    t1, err := template.ParseFiles("src/web/template/html/index.html")
    if err != nil {
        panic(err)
    }
    t1.Execute(w, "Hello MyHTML")
}
```

模板语法要点：

- **空格**：`{{ 1 }}` 输出 ` 1 `；`{{- 1 -}}` 去除两侧空白，输出 `1`。
- **注释**：`{{/* xxoo */}}`。
- **pipeline 多级传递**：类似 Unix 管道，前一个命令的结果传给后一个命令的最后一个参数。以下都输出 `shenzhuan`：

  ```
  {{"shenzhuan"}}
  {{printf "%q" "shenzhuan"}}
  {{"shenzhuan" | printf "%q"}}
  {{"zhuan" | printf "%s%s" "shen" | printf "%q"}}
  {{"shenzhuan" | printf "%s" | printf "%q"}}
  ```

- **变量**：`$var := pipeline`（定义新变量）；`$var = pipeline`（赋值）。
- **条件判断**：比较运算符 `eq ne lt le gt ge`。

  ```
  {{$Age := 19}}
  {{if ge $Age 18}}
  恭喜你成年了！
  {{end}}

  {{$Age := 13}}
  {{if ge $Age 18}}
  恭喜你成年了！
  {{else if lt $Age 14}}
  远离
  {{else}}
  禁止入内
  {{end}}
  ```

- **循环**：

  ```
  strs := []string{"图灵教育", "申专", "666"}
  t1.Execute(w, strs)

  {{range $val := .}}
  {{println $val}}
  {{end}}
  ```

- **设置 `.` 的值**：`with...end`，如 `{{with lt $Age 14}}ssssss{{else}}XXXXXXXXXXXX{{end}}`。
- 更多 API 见 [studygolang.com/pkgdoc](https://studygolang.com/pkgdoc)，源码见 `template/funcs.go`。

**嵌套 HTML**：使用 `define` 和 `template` 关键字。

```
header.html 中：
{{define "header"}}
    这是header
{{end}}

index.html 中：
{{template "header"}}

ServeHTTP 方法中：
t1, err := template.ParseFiles("src/web/template/html/index.html", "src/web/template/html/header.html")
```

### 3. 多路复用器 ServeMux

```go
func newServerMux(w http.ResponseWriter, r *http.Request) {
    fmt.Println(w, "my mux ")
}

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/", newServerMux)
    s := &http.Server{
        Addr:    ":8081",
        Handler: mux,
    }
    s.ListenAndServe()
    fmt.Println()
}
```

多个 handler（`/happy`、`/bad`）：

```go
func happy(w http.ResponseWriter, r *http.Request) {
    fmt.Println(w, "happy ")
}
func bad(w http.ResponseWriter, r *http.Request) {
    fmt.Println(w, "happy ")
}

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/", newServerMux)
    mux.HandleFunc("/happy", happy)
    mux.HandleFunc("/bad", bad)
    s := &http.Server{
        Addr:    ":8081",
        Handler: mux,
    }
    s.ListenAndServe()
    fmt.Println()
}
```

### 4. HttpRouter 高性能 HTTP 路由包

`ServeMux` 的缺陷是无法用变量实现 URL 模式匹配，而 `HttpRouter` 可以。它是高性能的第三方 HTTP 路由包，弥补了 `net/http` 路由的不足：支持路由模式中的变量、匹配请求方法，扩展性更好。Gin 框架即基于它开发。

```go
go get github.com/julienschmidt/httprouter

func Hello(w http.ResponseWriter, r *http.Request, _ httprouter.Params) {
    w.Write([]byte("hello httpRouter！！"))
}

func Index(w http.ResponseWriter, r *http.Request, ps httprouter.Params) {
    fmt.Fprintf(w, "hello %s \n", ps.ByName("name"))
}

func main() {
    router := httprouter.New()
    router.GET("/", Hello)
    router.GET("/index/:name", Index)
    http.ListenAndServe(":8081", router)
    fmt.Println()
}
```

RESTful 风格路由实现 CRUD：

```go
func ModifyUser(w http.ResponseWriter, r *http.Request, ps httprouter.Params) {
    uid := ps.ByName("uid")
    fmt.Fprintf(w, "修改了 用户id为 %s \n", uid)
}
func DeleteUser(w http.ResponseWriter, r *http.Request, ps httprouter.Params) {
    uid := ps.ByName("uid")
    fmt.Fprintf(w, "删除了 用户id为 %s \n", uid)
}

func main() {
    router := httprouter.New()
    router.GET("/", Hello)
    router.GET("/index/:name", Index)
    router.POST("/modifyuser/:uid", ModifyUser)
    router.DELETE("/deleteuser/:uid", DeleteUser)
    http.ListenAndServe(":8081", router)
    fmt.Println()
}
```

### 5. 网络模型

Linux 五种网络模型：

- **BIO**：阻塞 IO
- **NIO**：非阻塞 IO
- **多路复用**
  - **Select**：轮询遍历多个（上限 1024 个）fd 文件描述符，检查是否就绪
  - **Poll**：用 `pollfd` 结构表示要监听的描述符，需将 socket 从用户态转换到内核态
  - **Epoll**：事件监听，三个重要方法：
    - `epoll_create()`：创建一个 epoll 对象
    - `epoll_ctl()`：事件注册，维护一棵红黑树
    - `epoll_wait()`：等待就绪事件，已就绪事件维护在一个双向链表中

### 6. goroutine + epoll 网络模型

**通信原理**：BIO → NIO → Selector → Poll → Epoll。

**Golang 网络通信**：多协程 + Epoll。

**MPG 调度与 Epoll 的关联**：MPG 模型中，IO 事件发生时，之前的 G 与 g0 协程如何获得执行权？协程主方法 `main` 最终调用 `gopark()`，该关键方法与 Epoll 网络模型关联，让出当前协程执行权，一般返回到 g0 让 g0 重新调度。

**源码解读（net.Listen）**：

```go
net.Listen("tcp", "0.0.0.0:8082")

func Listen(network, address string) (Listener, error) {
    var lc ListenConfig
    return lc.Listen(context.Background(), network, address)
}

func (lc *ListenConfig) Listen(ctx context.Context, network, address string) (Listener, error) {
    addrs, err := DefaultResolver.resolveAddrList(ctx, "listen", network, address, nil)
    if err != nil {
        return nil, &OpError{Op: "listen", Net: network, Source: nil, Addr: nil, Err: err}
    }
    sl := &sysListener{ListenConfig: *lc, network: network, address: address}
    var l Listener
    la := addrs.first(isIPv4)
    switch la := la.(type) {
    case *TCPAddr:
        l, err = sl.listenTCP(ctx, la) // TCP 监听
    case *UnixAddr:
        l, err = sl.listenUnix(ctx, la)
    default:
        return nil, &OpError{Op: "listen", Net: sl.network, Source: nil, Addr: la, Err: &AddrError{Err: "unexpected address type", Addr: address}}
    }
    if err != nil {
        return nil, &OpError{Op: "listen", Net: sl.network, Source: nil, Addr: la, Err: err}
    }
    return l, nil
}

// listenTCP 返回值包含关键的 poll.FD
func (sl *sysListener) listenTCP(ctx context.Context, laddr *TCPAddr) (*TCPListener, error) {
    fd, err := internetSocket(ctx, sl.network, laddr, nil, syscall.SOCK_STREAM, 0, "listen", sl.ListenConfig.Control)
    if err != nil {
        return nil, err
    }
    return &TCPListener{fd: fd, lc: sl.ListenConfig}, nil
}

func socket(ctx context.Context, net string, family, sotype, proto int, ipv6only bool, laddr, raddr sockaddr, ctrlFn func(string, string, syscall.RawConn) error) (fd *netFD, err error) {
    // 1. 根据操作系统获取对应的 socket
    s, err := sysSocket(family, sotype, proto)
    if err != nil {
        return nil, err
    }
    // 2. 设置 socket 选项
    if err = setDefaultSockopts(s, family, sotype, ipv6only); err != nil {
        poll.CloseFunc(s)
        return nil, err
    }
    // 3. 创建 fd
    if fd, err = newFD(s, family, sotype, net); err != nil {
        poll.CloseFunc(s)
        return nil, err
    }
    // 4. 监听（负责调用系统的 bind 和 listen）
    if laddr != nil && raddr == nil {
        switch sotype {
        case syscall.SOCK_STREAM, syscall.SOCK_SEQPACKET:
            if err := fd.listenStream(laddr, listenerBacklog(), ctrlFn); err != nil {
                fd.Close()
                return nil, err
            }
            return fd, nil
        case syscall.SOCK_DGRAM:
            if err := fd.listenDatagram(laddr, ctrlFn); err != nil {
                fd.Close()
                return nil, err
            }
            return fd, nil
        }
    }
    // 5. 发起连接，非 listen socket 处理
    if err := fd.dial(ctx, laddr, raddr, ctrlFn); err != nil {
        fd.Close()
        return nil, err
    }
    return fd, nil
}
```

**源码解读（net.Dial）**：

```go
conn, err := net.Dial("tcp", "192.168.49.254:8082")

func Dial(network, address string) (Conn, error) {
    var d Dialer
    return d.Dial(network, address) // 实际调用 DialContext
}

// 最终返回的 TCPConn > Conn 都基于关键网络描述符 netFD
func (d *Dialer) DialContext(ctx context.Context, network, address string) (Conn, error) {
    ...
    // 连接建立后设置 KeepAlive
    if tc, ok := c.(*TCPConn); ok && d.KeepAlive >= 0 {
        setKeepAlive(tc.fd, true)
        ka := d.KeepAlive
        if d.KeepAlive == 0 {
            ka = defaultTCPKeepAlive
        }
        setKeepAlivePeriod(tc.fd, ka)
        testHookSetKeepAlive(ka)
    }
    return c, nil
}
```

**netFD 网络描述符**（server 创建 socket 时已构建）：

```go
func newFD(sysfd syscall.Handle, family, sotype int, net string) (*netFD, error) {
    ret := &netFD{
        pfd: poll.FD{
            Sysfd:         sysfd,
            IsStream:      sotype == syscall.SOCK_STREAM,
            ZeroReadIsEOF: sotype != syscall.SOCK_DGRAM && sotype != syscall.SOCK_RAW,
        },
        family: family,
        sotype: sotype,
        net:    net,
    }
    return ret, nil
}

type conn struct {
    fd *netFD // 关键网络描述符/句柄，不论 net.Listener 还是 Dial 都基于此
}

type netFD struct {
    // 包含两个重要数据结构：Sysfd 和 pollDesc
    // 1. Sysfd 是真正的系统文件描述符
    // 2. pollDesc 是对底层事件驱动的封装，所有读写超时等操作都通过它实现
    pfd poll.FD

    family      int
    sotype      int
    isConnected bool
    net         string
    laddr       Addr
    raddr       Addr
}

type FD struct {
    fdmu  fdMutex       // 读写锁，锁定 sysfd 并序列化对 Read/Write 的访问
    Sysfd syscall.Handle // 系统文件描述符
    rop   operation     // 读操作
    wop   operation     // 写操作
    pd    pollDesc      // 底层事件驱动的封装
    l     sync.Mutex    // 用于实现 pread/pwrite

    csema         uint32   // 关闭文件时的信号
    skipSyncNotif bool     // 是否跳过 sync
    IsStream      bool     // TCP 还是 UDP
    ZeroReadIsEOF bool     // 读到 0 字节时是否为错误，基于 socket 时为 false
    isFile        bool     // 系统真实文件还是网络 socket 连接
    kind          fileKind // 文件类型
}
```

**pollDesc**（用户态与内核态资源共享的关键）：

```go
func (pd *pollDesc) init(fd *FD) error {
    serverInit.Do(runtime_pollServerInit) // 首次初始化
    // 注册 epoll 实例到 fd，实际 link 到 runtime 包的 poll_runtime_pollOpen，
    // 具体实现在 runtime/netpoll.go
    //go:linkname poll_runtime_pollOpen internal/poll.runtime_pollOpen
    ctx, errno := runtime_pollOpen(uintptr(fd.Sysfd))
    if errno != 0 {
        return errnoErr(syscall.Errno(errno))
    }
    pd.runtimeCtx = ctx
    return nil
}

// runtime/netpoll.go 中的 pollDesc
type pollDesc struct {
    link    *pollDesc
    lock    mutex
    fd      uintptr
    closing bool
    everr   bool
    user    uint32
    rseq    uintptr

    // 保存用户态读协程地址：
    // 用户态协程调用 read 阻塞时 rg 设为该协程，
    // 内核态 epoll_wait 检测到 read 就绪后通过 rg 找到该协程并恢复运行。
    // pollDesc 实现用户态与内核态资源共享就在于此。
    rg uintptr // pdReady、pdWait、G waiting for read 或 nil
    rt timer   // 读定时器，防止超时
    rd int64   // read deadline
    wseq uintptr
    wg uintptr // pdReady、pdWait、G waiting for write 或 nil
    wt timer   // 写定时器
    wd int64   // write deadline
    self *pollDesc
    // epoll 网络模型具体方法在 netpoll_epoll.go 中：epollcreate、epollwait、epollctl
}
```

**epoll 初始化**（通过 `sync.Once` 和 `netpollInited` 保证只执行一次）：

```go
func poll_runtime_pollServerInit() {
    netpollGenericInit()
}

func netpollGenericInit() {
    if atomic.Load(&netpollInited) == 0 {
        lockInit(&netpollInitLock, lockRankNetpollInit)
        lock(&netpollInitLock)
        if netpollInited == 0 {
            netpollinit() // 真正系统调用，link 到 netpoll_epoll.go
            atomic.Store(&netpollInited, 1)
        }
        unlock(&netpollInitLock)
    }
}

func netpollinit() {
    epfd = epollcreate1(_EPOLL_CLOEXEC)
    ...
}
```

### 7. 网络通信总结

1. 网络通信通过**多协程 + Epoll 事件驱动**的网络模型。
2. 简单、高效，内置规范。
3. 服务端与客户端如何关联交互。
4. 网络模型链路：`Conn > netFD > pollDesc (rg/wg) > epoll (epollcreate/epollctl/epollwait)`。
5. 详细流程：`init > open > netPoll (wait > broke/break > read > commit) > gopark 调度 G > close > free`。
6. Golang 协程 MPG 调度与网络通信的 G 调度都通过 `gopark` 调度 G。
7. 可定制化，自己封装使用。

## 二、进阶并发编程

### 1. 进程与线程

- **进程（Process）**：并发执行的程序中分配和管理资源的基本单位。
- **线程（Thread）**：进程的执行单元，是进行调度的实体，是比进程更小的独立运行单位。

### 2. 并发与并行

- **并发（Concurrent）**：多线程交替操作同一资源类。
- **并行（Parallel）**：多个线程同时操作多个资源类。

Erlang 之父 Joe Armstrong 用一张 5 岁小孩都能看懂的图解释了并发与并行的区别：

![并发与并行](images/1747395864128-2afa0fb4-86a4-4bd7-b999-8bb47ba23eb3.png)

### 3. 协程 goroutine

**需求**：统计 1~2000000 的数字中哪些是素数。传统方式用循环判断，优化方式是并发/并行，Golang 将统计分配给多个 goroutine 完成。

**协程基本概念**：协程是单线程下的并发，又称微线程、纤程，是比线程更小的执行单元。它自带 CPU 上下文，只要在合适时机，就能把一个协程切换到另一个协程（英文名 Coroutine）。

一句话概括：协程是轻量级的线程，拥有独立栈空间、共享程序堆空间，调度由用户控制，是逻辑态，对资源消耗小。

**线程与协程的区别**：

- 线程切换是 CPU 在不同线程间来回切换，属于系统层面，不止保存和恢复 CPU 上下文那么简单，非常耗费性能。
- 协程只是同一线程内来回切换不同函数，只是简单的操作 CPU 上下文，性能消耗大大减少。
- Golang 的协程机制可轻松开启上万个协程；其他语言的并发机制一般基于线程，开启过多资源耗费大。

**案例**：主线程开启一个 goroutine 每隔 1s 输出"马士兵教育申专你好！"，主线程每隔 2s 输出 go routine，十次后退出程序，要求主线程和 goroutine 同时执行。

![goroutine 流程图](images/1747395890932-d4b5401a-c2f9-463d-9518-9ccdde19cee7.png)

## 三、Go 语言常见面试题

### 1. Go 语言的特点

- **简洁性**：语法相对简单，易于学习和使用。
- **并发支持**：内置 goroutine 和 channel，并发编程简单。
- **高性能**：编译型语言，性能接近 C/C++。
- **垃圾回收**：自动垃圾回收，减少内存管理的复杂性。
- **强类型**：强类型语言，类型安全性高。
- **跨平台**：可编译为不同平台的二进制文件，支持多种操作系统。

### 2. Go 语言中的数据类型

- **基本数据类型**：
  - 整数类型：`int`、`int8`、`int16`、`int32`、`int64`
  - 无符号整数类型：`uint`、`uint8`、`uint16`、`uint32`、`uint64`
  - 浮点数类型：`float32`、`float64`
  - 布尔类型：`bool`
  - 字符串类型：`string`
- **复合数据类型**：
  - 数组：`[n]type`
  - 切片：`[]type`
  - 结构体：`struct`
  - 映射：`map[keyType]valueType`
  - 通道：`chan type`

### 3. 如何定义接口？

使用 `type` 关键字定义接口。

### 4. 什么是 goroutine？如何启动一个 goroutine？

goroutine 是 Go 语言中的轻量级线程。使用 `go` 关键字即可启动一个新的 goroutine，例如 `go myFunction()`。Go 运行时负责管理这些 goroutine 并调度它们的执行。

```go
go func() {
    fmt.Println("Hello from goroutine")
}()
```

### 5. 什么是通道（channel），如何使用？

通道是 Go 中用于 goroutine 之间通信的机制，可以安全地传递数据，避免使用锁的复杂性。用 `make` 创建通道：

```go
ch := make(chan int)
```

通过 `<-` 操作符发送和接收数据。

### 6. select 语句的用途？

`select` 用于等待多个通道操作，能处理多个通道的发送和接收，它会阻塞直到其中一个通道准备好进行操作。

### 7. Go 语言如何处理错误？

Go 没有异常处理机制，而是通过返回值处理错误。函数通常返回一个 error 类型的值，调用者需检查该值判断是否出错。

```go
func divide(a, b int) (int, error) {
    if b == 0 {
        return 0, fmt.Errorf("division by zero")
    }
    return a / b, nil
}

// 调用
result, err := divide(10, 0)
if err != nil {
    fmt.Println("Error:", err)
} else {
    fmt.Println("Result:", result)
}
```

### 8. 如何定义一个自定义错误类型？

通过实现 `Error()` 方法定义自定义错误类型：

```go
type MyError struct {
    Message string
}

func (e *MyError) Error() string {
    return e.Message
}
```

### 9. defer 的作用？

`defer` 用于注册一个函数，在包含它的函数执行完毕后执行，常用于资源清理、解锁等操作。

```go
func main() {
    defer fmt.Println("World")
    fmt.Println("Hello")
}

// 输出：
// Hello
// World
```

### 10. 如何进行单元测试？

使用 `testing` 包进行单元测试，测试文件以 `_test.go` 结尾，测试函数以 `Test` 开头。

```go
package main

import "testing"

func TestAdd(t *testing.T) {
    result := Add(1, 2)
    if result != 3 {
        t.Errorf("Expected 3, got %d", result)
    }
}
```

运行测试：

```bash
go test
```
