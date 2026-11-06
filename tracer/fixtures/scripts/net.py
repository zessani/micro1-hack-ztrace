import errno
import select
import socket

s = socket.socket()
s.setblocking(False)
rc = s.connect_ex(("127.0.0.1", 6379))
print("nonblocking connect rc", errno.errorcode.get(rc, rc))
select.select([], [s], [], 2)
err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
print("so_error", errno.errorcode.get(err, err))
s.close()

s = socket.create_connection(("127.0.0.1", 8081), timeout=2)
print("got", s.recv(10))
s.close()

s = socket.socket()
try:
    s.connect(("127.0.0.1", 6380))
except OSError as e:
    print("blocking refused", e.errno)
s.close()

s = socket.socket(socket.AF_INET6)
try:
    s.connect(("::1", 6381))
except OSError as e:
    print("v6 refused", e.errno)
s.close()

s = socket.socket()
s.setblocking(False)
s.connect_ex(("10.77.0.10", 80))
s.close()
