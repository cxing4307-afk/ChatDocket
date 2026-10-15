import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .library import ImageCollection, scan_folder
from .pdf_export import export_pdf


class AppState:
    def __init__(self):
        self.collection = ImageCollection([])
        self.lock = threading.Lock()

    def image_dicts(self):
        return [image.as_dict() for image in self.collection.images]


class ChatDocketServer(ThreadingHTTPServer):
    def __init__(self, address, state):
        super().__init__(address, ChatDocketHandler)
        self.state = state


class ChatDocketHandler(BaseHTTPRequestHandler):
    server_version = "ChatDocket/0.1"

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _payload(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ValueError("Request is too large")
            return json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError("Send a valid JSON request") from error

    def do_POST(self):
        try:
            payload = self._payload()
            with self.server.state.lock:
                response = self._dispatch_post(urlparse(self.path).path, payload)
            self._json(200, response)
        except (KeyError, TypeError, ValueError, OSError) as error:
            self._json(400, {"error": str(error)})

    def _dispatch_post(self, path, payload):
        if path == "/api/import":
            images = scan_folder(payload.get("folder", ""))
            self.server.state.collection = ImageCollection(images)
            return {"images": self.server.state.image_dicts()}
        if path == "/api/reorder":
            self.server.state.collection.reorder(payload.get("ids", []))
            return {"images": self.server.state.image_dicts()}
        if path == "/api/export":
            output = export_pdf(
                self.server.state.collection.images,
                payload.get("output", ""),
                int(payload.get("perPage", 2)),
            )
            return {"output": str(output)}
        raise ValueError("Unknown API endpoint")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/images":
            with self.server.state.lock:
                self._json(200, {"images": self.server.state.image_dicts()})
            return
        if parsed.path == "/api/thumbnail":
            self._thumbnail(parse_qs(parsed.query).get("id", [""])[0])
            return
        self._static(parsed.path)

    def _thumbnail(self, image_id):
        with self.server.state.lock:
            record = next(
                (item for item in self.server.state.collection.images if item.id == image_id),
                None,
            )
        if record is None:
            self._json(404, {"error": "Screenshot not found"})
            return
        body = record.path.read_bytes()
        content_type = "image/png" if record.path.suffix.casefold() == ".png" else "image/jpeg"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, request_path):
        filename = "index.html" if request_path == "/" else request_path.lstrip("/")
        if filename not in {"index.html", "app.css", "app.js"}:
            self.send_error(404)
            return
        path = Path(__file__).with_name("static") / filename
        if not path.exists():
            self.send_error(404)
            return
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_types[path.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(host="127.0.0.1", port=8765, state=None):
    return ChatDocketServer((host, port), state or AppState())


def main():
    parser = argparse.ArgumentParser(description="Run ChatDocket on this computer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    print(f"ChatDocket is ready at http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping ChatDocket")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
