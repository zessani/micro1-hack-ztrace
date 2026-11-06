const fs = require('fs');
const net = require('net');
const { spawnSync, spawn } = require('child_process');

const S = '/opt/zbench/tracer/fixtures/scripts';

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', cwd: '/work/repo', ...opts });
  return r.status;
}

const server = net.createServer((sock) => sock.end('hello\n'));
server.listen(8081, '127.0.0.1', async () => {
  fs.writeFileSync('/home/agent/agent-own.txt', 'agent\n');
  await new Promise((resolve) => {
    const c = net.connect(8081, '127.0.0.1', () => { c.end(); resolve(); });
    c.on('error', resolve);
  });
  await fs.promises.writeFile('/home/agent/agent-async.txt', 'x');
  run('python3', ['-c', "open('/work/repo/agent-direct.txt','w').write('x')"]);

  run('bash', ['-c', [
    'echo start',
    'echo data > /work/repo/a.txt',
    'mkdir -p /home/agent/.cache/zb',
    'echo c > /home/agent/.cache/zb/c.txt',
    'mv /work/repo/a.txt /work/repo/b.txt',
    'rm /work/repo/b.txt',
    'cd sub && echo rel > rel.txt && cd deeper && touch ../../top.txt',
    `python3 ${S}/child.py`,
    'echo oops >&2',
  ].join('; ')]);

  await new Promise((resolve) => {
    const p = spawn('bash', ['-c', `python3 ${S}/net.py`], { stdio: 'inherit', cwd: '/work/repo' });
    p.on('exit', resolve);
  });

  run('bash', ['-c', 'exit 3']);
  run('sh', ['-c', 'env bash -c "echo nested > /work/repo/nested.txt"']);
  run('/bin/bash', ['-c', 'cd /work/repo/sub; node -e "require(\'fs\').writeFileSync(\'from-node.txt\', \'n\')"']);

  server.close();
  fs.writeFileSync('/work/report.json', '{}');
  process.exit(0);
});
