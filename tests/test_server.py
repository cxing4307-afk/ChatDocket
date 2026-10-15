import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image

from chatdocket.server import AppState, make_server


def post(base_url, path, payload):
    request = Request(
        base_url + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request) as response:
        return response.status, json.load(response)


def start_server():
    server = make_server("127.0.0.1", 0, AppState())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def test_import_reorder_and_export_over_http(tmp_path):
    Image.new("RGB", (100, 180), "white").save(tmp_path / "chat-1.png")
    Image.new("RGB", (100, 180), "gray").save(tmp_path / "chat-2.png")
    server, base_url = start_server()
    try:
        status, imported = post(base_url, "/api/import", {"folder": str(tmp_path)})
        assert status == 200
        assert [item["filename"] for item in imported["images"]] == [
            "chat-1.png",
            "chat-2.png",
        ]

        ids = [item["id"] for item in reversed(imported["images"])]
        _, reordered = post(base_url, "/api/reorder", {"ids": ids})
        assert [item["filename"] for item in reordered["images"]] == [
            "chat-2.png",
            "chat-1.png",
        ]

        output = tmp_path / "packet.pdf"
        _, exported = post(
            base_url,
            "/api/export",
            {"output": str(output), "perPage": 2},
        )
        assert exported == {"output": str(output)}
        assert output.read_bytes().startswith(b"%PDF-")
    finally:
        server.shutdown()
        server.server_close()


def test_api_returns_a_json_error_for_bad_input(tmp_path):
    server, base_url = start_server()
    try:
        try:
            post(base_url, "/api/import", {"folder": str(tmp_path / "missing")})
        except HTTPError as error:
            assert error.code == 400
            assert json.load(error)["error"] == "Choose an existing folder"
        else:
            raise AssertionError("request should fail")
    finally:
        server.shutdown()
        server.server_close()
