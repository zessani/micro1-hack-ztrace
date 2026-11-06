import os
import sys
import threading

with open("child-rel.txt", "w") as f:
    f.write("rel\n")
os.chdir("/work/repo/sub")
with open("moved-src.txt", "w") as f:
    f.write("m\n")
os.rename("moved-src.txt", "moved-dst.txt")
os.unlink("moved-dst.txt")
os.makedirs("newdir/inner", exist_ok=True)


def worker():
    with open("/work/repo/from-thread.txt", "w") as f:
        f.write("t\n")
    print("thread says hi", flush=True)


t = threading.Thread(target=worker)
t.start()
t.join()
fd = os.open("newdir", os.O_RDONLY | os.O_DIRECTORY)
os.fchdir(fd)
open("in-newdir.txt", "a").close()
d = os.open("/home/agent/.cache", os.O_RDONLY | os.O_DIRECTORY)
os.open("viadirfd.txt", os.O_WRONLY | os.O_CREAT, 0o644, dir_fd=d)
os.rename("viadirfd.txt", "viadirfd2.txt", src_dir_fd=d, dst_dir_fd=d)
print("child done ✓ \"quoted\"\tTab")
print("to stderr", file=sys.stderr)
sys.exit(0)
