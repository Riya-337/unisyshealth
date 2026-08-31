import server from '../dist/server/server.js';

export const config = {
  runtime: 'nodejs',
};

export default async function handler(req, res) {
  if (typeof Request !== 'undefined' && req instanceof Request) {
    return server.fetch(req);
  }

  const host = req.headers['x-forwarded-host'] || req.headers.host || 'localhost';
  const proto = req.headers['x-forwarded-proto'] || 'https';
  const url = `${proto}://${host}${req.url}`;

  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (value) {
      if (Array.isArray(value)) {
        value.forEach((v) => headers.append(key, v));
      } else {
        headers.set(key, value);
      }
    }
  }

  let body = undefined;
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    body = req;
  }

  const webRequest = new Request(url, {
    method: req.method,
    headers,
    body,
    duplex: 'half',
  });

  const response = await server.fetch(webRequest);

  res.statusCode = response.status;
  response.headers.forEach((value, key) => {
    res.setHeader(key, value);
  });

  if (response.body) {
    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(value);
    }
  }
  res.end();
}
