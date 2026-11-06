import socket

print(sorted({a[4][0] for a in socket.getaddrinfo("localhost", 6379)}))
try:
    socket.create_connection(("localhost", 6379), timeout=2)
except OSError as e:
    print("closed", e.errno)

srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 6390))
srv.listen(1)
c = socket.create_connection(("localhost", 6390), timeout=2)
print("open ok")
c.close()
srv.close()
