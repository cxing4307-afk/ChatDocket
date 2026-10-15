import json
import threading
import base64
import io
from pathlib import Path
from time import sleep
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from PIL import Image
import pytest

from chatdocket.library import ImageCollection
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


def test_home_page_serves_the_folder_workspace():
    server, base_url = start_server()
    try:
        with urlopen(base_url) as response:
            page = response.read().decode()
        assert response.status == 200
        assert "Drop a screenshot folder here" in page
        assert "Does not verify evidence" in page
    finally:
        server.shutdown()
        server.server_close()


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


def test_upload_accepts_browser_folder_files():
    image = io.BytesIO()
    Image.new("RGB", (60, 100), "white").save(image, "PNG")
    server, base_url = start_server()
    try:
        _, result = post(
            base_url,
            "/api/upload",
            {
                "files": [
                    {
                        "name": "chat-7.png",
                        "data": base64.b64encode(image.getvalue()).decode(),
                        "modified": 1_772_700_000_000,
                    }
                ]
            },
        )
        assert result["images"][0]["filename"] == "chat-7.png"
    finally:
        server.shutdown()
        server.server_close()


def test_failed_upload_keeps_the_previous_session_files():
    image = io.BytesIO()
    Image.new("RGB", (60, 100), "white").save(image, "PNG")
    state = AppState()
    try:
        images = state.replace_uploads(
            [{"name": "chat-1.png", "data": base64.b64encode(image.getvalue()).decode()}]
        )
        state.collection = ImageCollection(images)

        with pytest.raises(ValueError, match="Could not read chat-2.png"):
            state.replace_uploads([{"name": "chat-2.png", "data": "not base64"}])

        assert state.collection.images[0].path.exists()
    finally:
        state.close()


def test_thumbnail_read_finishes_before_replacing_uploads(monkeypatch):
    image = io.BytesIO()
    Image.new("RGB", (60, 100), "white").save(image, "PNG")
    encoded = base64.b64encode(image.getvalue()).decode()
    server, base_url = start_server()
    started = threading.Event()
    allow_read = threading.Event()
    upload_finished = threading.Event()
    try:
        _, imported = post(
            base_url, "/api/upload", {"files": [{"name": "chat-1.png", "data": encoded}]}
        )
        target = Path(imported["images"][0]["id"])
        original_read_bytes = Path.read_bytes

        def delayed_read_bytes(path):
            if path == target:
                started.set()
                allow_read.wait(timeout=2)
            return original_read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", delayed_read_bytes)
        thumbnail = threading.Thread(
            target=lambda: urlopen(f"{base_url}/api/thumbnail?id={quote(str(target))}").read()
        )
        thumbnail.start()
        assert started.wait(timeout=2)

        def replace_upload():
            post(base_url, "/api/upload", {"files": [{"name": "chat-2.png", "data": encoded}]})
            upload_finished.set()

        upload = threading.Thread(target=replace_upload)
        upload.start()
        sleep(0.1)
        assert not upload_finished.is_set()
        allow_read.set()
        thumbnail.join(timeout=2)
        upload.join(timeout=2)
        assert upload_finished.is_set()
    finally:
        allow_read.set()
        server.shutdown()
        server.server_close()
