"""Agency B's API, simulated. Start it with:  python -m sources.api

GET /listings?date=YYYY-MM-DD

The first request for each date fails with a 503, like a real API having a bad moment.
"""

import os
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from sources import generate

PORT = 8081
_seen_dates: set[str] = set()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        day = parse_qs(url.query).get("date", [""])[0]
        if url.path != "/listings" or not day:
            return self._send(404, '{"error": "use /listings?date=YYYY-MM-DD"}')
        if day not in _seen_dates:
            _seen_dates.add(day)
            return self._send(503, '{"error": "service temporarily unavailable"}')
        self._send(200, generate.render_b(date.fromisoformat(day)))

    def _send(self, status: int, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    # Inside a container the server must listen on all addresses, not only on localhost.
    host = os.environ.get("AGENCY_B_HOST", "localhost")
    print(f"Agency B API listening on http://{host}:{PORT}", flush=True)
    ThreadingHTTPServer((host, PORT), Handler).serve_forever()
