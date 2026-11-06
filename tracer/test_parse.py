import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tracer.parse import build_facts, cstring, split_args

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
TASK = FIX / "task.toml"


def by_argv(facts, *argv):
    return [p for p in facts["processes"] if p["argv"][: len(argv)] == list(argv)]


def events(facts):
    return {(e["op"], e["path"]) for e in facts["file_events"]}


def synth(lines, root_is_command=False, cwd="/work/repo", task=None):
    d = tempfile.mkdtemp()
    Path(d, "trace.log").write_text("\n".join(lines) + "\n")
    Path(d, "ztrace.meta").write_text(f"root_is_command={int(root_is_command)}\ncwd={cwd}\n")
    return build_facts(d, task)


class FakeAgentTrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = build_facts(FIX / "fake_agent", TASK)

    def test_schema(self):
        f = self.f
        self.assertEqual(f["schema"], "zbench.facts/1")
        self.assertEqual(f["repo_root"], "/work/repo")
        self.assertEqual(f["tracer_version"], "0.1")
        self.assertEqual(set(f), {"schema", "repo_root", "root_pid", "processes", "file_events",
                                  "connections", "outputs", "tracer_version"})
        root = [p for p in f["processes"] if p["pid"] == f["root_pid"]][0]
        self.assertEqual(root["argv"][0], "node")
        self.assertIsNone(root["ppid"])
        self.assertEqual(root["scope"], "agent")
        self.assertEqual(root["exit_code"], 0)
        self.assertEqual(root["t_start"], 0.0)

    def test_scope(self):
        f = self.f
        direct = by_argv(f, "python3", "-c")[0]
        self.assertEqual(direct["scope"], "agent")
        self.assertIsNone(direct["command_root_pid"])
        shell = [p for p in by_argv(f, "bash", "-c") if p["argv"][2].startswith("echo start")][0]
        self.assertEqual(shell["scope"], "command")
        self.assertEqual(shell["command_root_pid"], shell["pid"])
        self.assertEqual(shell["ppid"], f["root_pid"])
        for name in ("mkdir", "mv", "rm", "touch"):
            p = by_argv(f, name)[0]
            self.assertEqual((p["scope"], p["command_root_pid"], p["ppid"]), ("command", shell["pid"], shell["pid"]))
        sh = by_argv(f, "sh", "-c")[0]
        nested = by_argv(f, "bash", "-c", "echo nested > /work/repo/nested.txt")[0]
        self.assertEqual(nested["command_root_pid"], sh["pid"])
        self.assertEqual(nested["ppid"], sh["pid"])

    def test_agent_events_dropped(self):
        paths = {p for _, p in events(self.f)}
        for p in ("/home/agent/agent-own.txt", "/home/agent/agent-async.txt",
                  "/work/repo/agent-direct.txt", "/work/report.json"):
            self.assertNotIn(p, paths)
        self.assertTrue(all(e["pid"] != self.f["root_pid"] for e in self.f["file_events"]))

    def test_file_events(self):
        expected = {
            ("write", "/work/repo/a.txt"),
            ("mkdir", "/home/agent/.cache"),
            ("mkdir", "/home/agent/.cache/zb"),
            ("write", "/home/agent/.cache/zb/c.txt"),
            ("rename_from", "/work/repo/a.txt"),
            ("rename_to", "/work/repo/b.txt"),
            ("unlink", "/work/repo/b.txt"),
            ("write", "/work/repo/sub/rel.txt"),
            ("write", "/work/repo/top.txt"),
            ("write", "/work/repo/sub/deeper/child-rel.txt"),
            ("write", "/work/repo/sub/moved-src.txt"),
            ("rename_from", "/work/repo/sub/moved-src.txt"),
            ("rename_to", "/work/repo/sub/moved-dst.txt"),
            ("unlink", "/work/repo/sub/moved-dst.txt"),
            ("mkdir", "/work/repo/sub/newdir"),
            ("mkdir", "/work/repo/sub/newdir/inner"),
            ("write", "/work/repo/from-thread.txt"),
            ("write", "/work/repo/sub/newdir/in-newdir.txt"),
            ("write", "/home/agent/.cache/viadirfd.txt"),
            ("rename_from", "/home/agent/.cache/viadirfd.txt"),
            ("rename_to", "/home/agent/.cache/viadirfd2.txt"),
            ("write", "/work/repo/nested.txt"),
            ("write", "/work/repo/sub/from-node.txt"),
        }
        self.assertEqual(events(self.f), expected)

    def test_threads_fold_into_process(self):
        child = by_argv(self.f, "python3", "/opt/zbench/tracer/fixtures/scripts/child.py")[0]
        thread_write = [e for e in self.f["file_events"] if e["path"] == "/work/repo/from-thread.txt"][0]
        self.assertEqual(thread_write["pid"], child["pid"])
        pids = {p["pid"] for p in self.f["processes"]}
        self.assertNotIn(child["pid"] + 1, pids)
        self.assertEqual(child["cwd"], "/work/repo/sub/deeper")
        out = [o for o in self.f["outputs"] if o["pid"] == child["pid"] and o["fd"] == 1][0]
        self.assertIn("thread says hi", out["text"])

    def test_exit_codes(self):
        self.assertEqual(by_argv(self.f, "bash", "-c", "exit 3")[0]["exit_code"], 3)
        for p in self.f["processes"]:
            self.assertIsNotNone(p["t_end"])
            self.assertLessEqual(p["t_start"], p["t_end"])

    def test_connections(self):
        conns = [(c["ip"], c["port"], c["family"], c["result"], c["errno"], c["host"]) for c in self.f["connections"]]
        self.assertEqual(conns, [
            ("127.0.0.1", 6379, "inet", "inprogress_failed", "ECONNREFUSED", "localhost"),
            ("127.0.0.1", 8081, "inet", "inprogress_ok", None, "localhost"),
            ("127.0.0.1", 6380, "inet", "refused", "ECONNREFUSED", "localhost"),
            ("::1", 6381, "inet6", "refused", "ECONNREFUSED", None),
            ("10.77.0.10", 80, "inet", "inprogress_unknown", None, "mock.pkgs.internal"),
        ])
        net = by_argv(self.f, "python3", "/opt/zbench/tracer/fixtures/scripts/net.py")[0]
        self.assertTrue(all(c["pid"] == net["pid"] for c in self.f["connections"]))

    def test_outputs(self):
        outs = {(o["pid"], o["fd"]): o["text"] for o in self.f["outputs"]}
        texts = "".join(outs.values())
        self.assertIn('child done ✓ "quoted"\tTab\n', texts)
        self.assertIn("to stderr\n", texts)
        self.assertIn("so_error ECONNREFUSED", texts)
        self.assertNotIn("data\n", texts)
        self.assertNotIn("rel\n", texts)
        self.assertTrue(all(not o["truncated"] for o in self.f["outputs"]))


class SolveTrace(unittest.TestCase):
    def test_root_is_command(self):
        f = build_facts(FIX / "solve", TASK)
        root = f["processes"][0]
        self.assertEqual(root["pid"], f["root_pid"])
        self.assertEqual((root["scope"], root["command_root_pid"]), ("command", root["pid"]))
        self.assertTrue(all(p["scope"] == "command" and p["command_root_pid"] == root["pid"] for p in f["processes"]))
        self.assertEqual(events(f), {
            ("write", "/work/repo/fixed.py"),
            ("mkdir", "/work/repo/build"),
            ("write", "/work/repo/build/out.bin"),
            ("rename_from", "/work/repo/build/out.bin"),
            ("rename_to", "/work/repo/final.bin"),
        })
        self.assertEqual([(o["fd"], o["text"]) for o in f["outputs"]], [(1, "solve done\n")])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, "facts.json")
            subprocess.run([sys.executable, "-m", "tracer.parse", str(FIX / "solve"), "--task", str(TASK),
                            "--root-is-command", "-o", str(out)], check=True, cwd=HERE.parent)
            self.assertEqual(json.loads(out.read_text())["schema"], "zbench.facts/1")


class Synthetic(unittest.TestCase):
    def test_strings(self):
        self.assertEqual(cstring(r'"a\"b\\c\n\t\342\234\223\x41\0"'), b'a"b\\c\n\t\xe2\x9c\x93A\x00')
        self.assertEqual(cstring('"abc"...'), b"abc")
        args, end = split_args('3</a,b (x)>, "x, \\"y)", [1, 2], {a=1, b=[2]}) = 0')
        self.assertEqual(args, ['3</a,b (x)>', '"x, \\"y)"', "[1, 2]", "{a=1, b=[2]}"])

    def test_unfinished_resumed_and_threads(self):
        f = synth([
            '10 1.000000 execve("/usr/bin/bash", ["bash", "-c", "x"], 0x1 /* 3 vars */) = 0',
            '10 1.100000 clone3({flags=CLONE_VM|CLONE_FS|CLONE_THREAD|CLONE_SETTLS, child_tid=0x1}, 88 <unfinished ...>',
            '11 1.150000 openat(AT_FDCWD</work/repo>, "t.txt", O_WRONLY|O_CREAT|O_TRUNC, 0666 <unfinished ...>',
            '10 1.160000 <... clone3 resumed> => {parent_tid=[11]}, 88) = 11',
            '11 1.170000 <... openat resumed>) = 3</work/repo/t.txt>',
            '11 1.200000 clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|SIGCHLD <unfinished ...>',
            '12 1.210000 chdir("sub") = 0',
            '11 1.220000 <... clone resumed>, child_tidptr=0x1) = 12',
            '12 1.230000 mkdir("d", 0777) = 0',
            '12 1.240000 rename("d", "/tmp/../tmp/e") = 0',
            '12 1.250000 unlink("gone") = 0',
            '12 1.255000 unlink("missing") = -1 ENOENT (No such file or directory)',
            '12 1.260000 creat("c.txt", 0644) = 4',
            '12 1.270000 open("r.txt", O_RDONLY) = 5',
            '12 1.280000 unlinkat(AT_FDCWD</work/repo/sub>, "dd", AT_REMOVEDIR) = 0',
            '12 1.300000 +++ killed by SIGKILL +++',
            '11 1.400000 +++ exited with 0 +++',
            '10 1.500000 exit_group(2) = ?',
            '10 1.500100 +++ exited with 2 +++',
        ], root_is_command=True)
        self.assertEqual([p["pid"] for p in f["processes"]], [10, 12])
        child = f["processes"][1]
        self.assertEqual((child["ppid"], child["signal"], child["exit_code"], child["argv"]), (10, "SIGKILL", None, ["bash", "-c", "x"]))
        self.assertEqual(f["processes"][0]["exit_code"], 2)
        self.assertEqual([(e["pid"], e["op"], e["path"]) for e in f["file_events"]], [
            (10, "write", "/work/repo/t.txt"),
            (12, "mkdir", "/work/repo/sub/d"),
            (12, "rename_from", "/work/repo/sub/d"),
            (12, "rename_to", "/tmp/e"),
            (12, "unlink", "/work/repo/sub/gone"),
            (12, "write", "/work/repo/sub/c.txt"),
        ])
        self.assertEqual(f["file_events"][0]["t"], 0.15)

    def test_scope_rule(self):
        f = synth([
            '1 1.0 execve("/usr/local/bin/node", ["node", "agent.js"], 0x1 /* 3 vars */) = 0',
            '1 1.1 clone(child_stack=NULL, flags=SIGCHLD) = 2',
            '2 1.2 execve("/usr/bin/git", ["git", "status"], 0x1 /* 3 vars */) = 0',
            '2 1.21 clone(child_stack=NULL, flags=SIGCHLD) = 4',
            '4 1.22 execve("/bin/sh", ["sh", "-c", "hook"], 0x1 /* 3 vars */) = 0',
            '4 1.23 openat(AT_FDCWD</work/repo>, "hook.out", O_WRONLY|O_CREAT, 0666) = 3</work/repo/hook.out>',
            '2 1.3 openat(AT_FDCWD</work/repo>, ".git/index.lock", O_RDWR|O_CREAT|O_EXCL, 0666) = 3</work/repo/.git/index.lock>',
            '1 1.4 vfork() = 3',
            '3 1.5 execve("/usr/bin/zsh", ["-zsh", "-c", "make"], 0x1 /* 3 vars */) = 0',
            '3 1.6 execve("/usr/bin/bash", ["bash", "-c", "y"], 0x1 /* 3 vars */) = 0',
            '3 1.7 openat(AT_FDCWD</work/repo>, "o.txt", O_WRONLY|O_APPEND, 0666) = 3</work/repo/o.txt>',
            '3 1.8 write(1</work/repo/o.txt>, "redirected\\n", 11) = 11',
            '3 1.9 write(1</dev/null>, "devnull\\n", 8) = 8',
            '3 2.0 write(1</tmp/harness.log>, "harness ", 8) = 8',
            '3 2.1 write(2<pipe:[5]>, "err\\n", 4) = 4',
            '3 2.2 writev(1<pipe:[4]>, [{iov_base="a", iov_len=1}, {iov_base="b\\n", iov_len=2}], 2) = 3',
            '1 2.3 write(1<pipe:[1]>, "agent says\\n", 11) = 11',
        ])
        scopes = {p["pid"]: (p["scope"], p["command_root_pid"]) for p in f["processes"]}
        self.assertEqual(scopes, {1: ("agent", None), 2: ("agent", None), 3: ("command", 3), 4: ("command", 4)})
        self.assertEqual(events(f), {("write", "/work/repo/o.txt"), ("write", "/work/repo/hook.out")})
        outs = {(o["pid"], o["fd"]): o["text"] for o in f["outputs"]}
        self.assertEqual(outs, {(3, 1): "harness ab\n", (3, 2): "err\n"})

    def test_superseded_exec(self):
        f = synth([
            '1 1.0 execve("/usr/bin/python3", ["python3"], 0x1 /* 3 vars */) = 0',
            '1 1.1 clone3({flags=CLONE_VM|CLONE_THREAD}, 88) = 2',
            '2 1.2 execve("/usr/bin/true", ["true"], 0x1 /* 3 vars */ <unfinished ...>',
            '1 1.3 +++ superseded by execve in pid 2 +++',
            '1 1.4 <... execve resumed>) = 0',
            '1 1.5 +++ exited with 0 +++',
        ])
        self.assertEqual([(p["pid"], p["argv"]) for p in f["processes"]], [(1, ["true"])])

    def test_connect_resolution(self):
        task = Path(tempfile.mkdtemp(), "task.toml")
        task.write_text('[hosts]\n"10.77.0.10" = "mock.pkgs.internal"\n')
        f = synth([
            '1 1.0 execve("/bin/sh", ["sh"], 0x1 /* 1 vars */) = 0',
            '1 1.1 connect(3<socket:[7]>, {sa_family=AF_INET, sin_port=htons(80), sin_addr=inet_addr("10.77.0.10")}, 16) = -1 EINPROGRESS (Operation now in progress)',
            '1 1.2 write(3<socket:[7]>, "GET /", 5) = 5',
            '1 1.3 connect(4<socket:[8]>, {sa_family=AF_INET6, sin6_port=htons(443), sin6_flowinfo=htonl(0), inet_pton(AF_INET6, "::ffff:10.77.0.10", &sin6_addr), sin6_scope_id=0}, 28) = -1 EINPROGRESS (Operation now in progress)',
            '1 1.4 getsockopt(4<socket:[8]>, SOL_SOCKET, SO_ERROR, [ETIMEDOUT], [4]) = 0',
            '1 1.5 connect(5<socket:[9]>, {sa_family=AF_INET, sin_port=htons(5432), sin_addr=inet_addr("10.0.0.9")}, 16) = -1 ETIMEDOUT (Connection timed out)',
            '1 1.6 connect(6<socket:[10]>, {sa_family=AF_INET, sin_port=htons(53), sin_addr=inet_addr("10.0.0.2")}, 16) = 0',
            '1 1.7 connect(7<socket:[11]>, {sa_family=AF_UNIX, sun_path="/run/x.sock"}, 110) = 0',
            '1 1.8 connect(8<socket:[12]>, {sa_family=AF_INET, sin_port=htons(1), sin_addr=inet_addr("10.0.0.1")}, 16) = -1 EINPROGRESS (Operation now in progress)',
            '1 1.9 connect(8<socket:[12]>, {sa_family=AF_INET, sin_port=htons(1), sin_addr=inet_addr("10.0.0.1")}, 16) = -1 ENETUNREACH (Network is unreachable)',
        ], root_is_command=True, task=str(task))
        got = [(c["ip"], c["port"], c["family"], c["host"], c["result"], c["errno"]) for c in f["connections"]]
        self.assertEqual(got, [
            ("10.77.0.10", 80, "inet", "mock.pkgs.internal", "inprogress_ok", None),
            ("10.77.0.10", 443, "inet6", "mock.pkgs.internal", "inprogress_failed", "ETIMEDOUT"),
            ("10.0.0.9", 5432, "inet", None, "timeout", "ETIMEDOUT"),
            ("10.0.0.2", 53, "inet", None, "ok", None),
            ("10.0.0.1", 1, "inet", None, "inprogress_failed", "ENETUNREACH"),
        ])

    def test_output_cap(self):
        chunk = "x" * 30000
        lines = ['1 1.0 execve("/bin/sh", ["sh"], 0x1 /* 1 vars */) = 0']
        lines += [f'1 1.{i} write(1<pipe:[1]>, "{chunk}", 30000) = 30000' for i in range(1, 4)]
        lines.append('1 1.9 write(1<pipe:[1]>, "THE END\\n", 8) = 8')
        f = synth(lines, root_is_command=True)
        out = f["outputs"][0]
        self.assertTrue(out["truncated"])
        self.assertTrue(out["text"].endswith("THE END\n"))
        self.assertLessEqual(len(out["text"].encode()), 64 * 1024 + 64)

    def test_relative_cwd_without_decorations(self):
        f = synth([
            '1 1.0 execve("/bin/bash", ["bash"], 0x1 /* 1 vars */) = 0',
            '1 1.1 chdir("pkg/../lib") = 0',
            '1 1.2 openat(AT_FDCWD, "a.py", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 3',
            '1 1.3 chdir("/tmp") = 0',
            '1 1.4 openat(AT_FDCWD, "b", O_RDWR) = 3',
            '1 1.5 openat(AT_FDCWD, "c", O_RDONLY|O_CLOEXEC) = 3',
            '1 1.6 openat(AT_FDCWD, "d", O_WRONLY|O_CREAT, 0666) = -1 EACCES (Permission denied)',
        ], root_is_command=True, cwd="/work/repo")
        self.assertEqual(events(f), {("write", "/work/repo/lib/a.py"), ("write", "/tmp/b")})


if __name__ == "__main__":
    unittest.main()
