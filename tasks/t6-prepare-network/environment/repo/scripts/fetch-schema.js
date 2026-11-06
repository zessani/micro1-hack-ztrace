const http = require('http');

const url = 'http://schemas.acme-internal.dev/v2/schema.json';
console.log(`prepare: fetching schema from ${url}`);

const req = http.get(url, { timeout: 5000 }, (res) => {
  let body = '';
  res.on('data', (c) => (body += c));
  res.on('end', () => {
    try {
      const schema = JSON.parse(body);
      console.log(`prepare: schema ${schema.version} ok (${res.statusCode})`);
    } catch (e) {
      console.log(`prepare: schema response not parseable (${res.statusCode})`);
    }
  });
});
req.on('timeout', () => req.destroy(new Error('timeout')));
req.on('error', (e) => console.log(`prepare: schema fetch failed: ${e.message}`));
