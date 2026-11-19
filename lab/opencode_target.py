"""Small, intentionally-vulnerable public-lab target for the OpenCode Pentester integration test.

Run: python3 lab/opencode_target.py [port]
It binds loopback only. Every flaw here is deliberate and limited to this fixture.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ORDERS = {
    1: {'id': 1, 'owner': 'alice', 'item': 'keyboard', 'card': '4111-1111-1111-1111'},
    2: {'id': 2, 'owner': 'bob', 'item': 'monitor', 'card': '5500-0000-0000-0004'},
    3: {'id': 3, 'owner': 'carol', 'item': 'headset', 'card': '4000-0000-0000-0002'},
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype='text/html; charset=utf-8', extra=None):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path, _, query = self.path.partition('?')
        if path == '/':
            self._send(200, """<!doctype html><title>Acme Shop</title>
<h1>Acme Shop</h1><p>Powered by acme-shop 1.4.2</p>
<form action="/search"><input name="q" placeholder="search products"><button>Search</button></form>
<ul><li><a href="/product?id=1">Product 1</a></li><li><a href="/admin">Admin</a></li></ul>""")
            return
        if path == '/search':
            value = query.split('q=', 1)[1] if 'q=' in query else ''
            self._send(200, f"<title>Search</title><h1>Results for {value}</h1><p>No products found.</p>")
            return
        if path == '/product':
            self._send(200, "<title>Product</title><h1>Product</h1><p>Keyboard, $49</p>")
            return
        if path.startswith('/api/orders/'):
            try:
                order_id = int(path.rsplit('/', 1)[1])
            except ValueError:
                self._send(400, json.dumps({'error': 'bad id'}), 'application/json')
                return
            order = ORDERS.get(order_id)
            if not order:
                self._send(404, json.dumps({'error': 'not found'}), 'application/json')
                return
            self._send(200, json.dumps(order), 'application/json')
            return
        if path == '/admin':
            self._send(200, "<title>Admin</title><h1>Admin panel</h1><p>No authentication configured.</p>")
            return
        if path == '/robots.txt':
            self._send(200, "User-agent: *\nDisallow: /admin\nDisallow: /backup\n", 'text/plain')
            return
        if path == '/backup':
            self._send(200, json.dumps({'db': 'acme.sqlite', 'api_key': 'demo-key-not-real'}), 'application/json')
            return
        if path == '/.git/config':
            self._send(200, "[core]\n\trepositoryformatversion = 0\n", 'text/plain')
            return
        self._send(404, '<h1>404</h1>')

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length).decode('utf-8', 'replace')
        if self.path == '/login':
            if "'" in body or '"' in body:
                self._send(500, "sqlite3.OperationalError: unrecognized token: \"'\"", 'text/plain')
            else:
                self._send(401, "<h1>Invalid credentials</h1>")
            return
        self._send(405, '<h1>Method not allowed</h1>')

    def log_message(self, *args):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18081
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'opencode lab target: http://127.0.0.1:{port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
