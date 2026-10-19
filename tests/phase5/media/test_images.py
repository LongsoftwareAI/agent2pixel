import base64
import struct
import zlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.console_media import create_console_media_router
from services.api.store import Store


def chunk(kind, payload=b""):
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def png(width=1, height=1, raw=b"\x00\xff\x00\x00", extra=b"", color=2):
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0))
        + extra
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND")
    )


@pytest.fixture
def api(tmp_path):
    app = FastAPI()
    app.state.store = Store(tmp_path)
    for wid in ("mine", "foreign"):
        app.state.store.put("workspace", dict(id=wid, name=wid))
    app.include_router(create_console_media_router(app))
    with TestClient(app) as client:
        yield client, app.state.store
    app.state.store.db.close()


def upload(client, data, **kwargs):
    return client.post(
        "/api/console/attachments/image",
        json=dict(
            workspace_id="mine",
            name="original.png",
            media_type="image/png",
            content_base64=base64.b64encode(data).decode(),
            **kwargs,
        ),
    )


def test_image_round_trip_scope_metadata_and_audit(api):
    client, store = api
    original = png()
    response = upload(client, original)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["pixel_interpretation"] == "unsupported"
    assert value["width"] == value["height"] == 1
    source = store.get("source", value["source_id"])
    assert "Image pixels not interpreted" in source["content"]
    assert "content_base64" not in value and "content_base64" not in source
    preview = client.get(value["preview_url"])
    assert preview.content == original
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert preview.headers["cache-control"] == "no-store"
    assert "sandbox" in preview.headers["content-security-policy"]
    assert (
        client.get(value["preview_url"].replace("mine", "foreign")).status_code == 404
    )
    assert (
        client.get(value["preview_url"].replace("mine", "missing")).status_code == 404
    )
    assert store.list("audit", "mine")[0]["action"] == "attachment.image.created"
    record = store.list("console_image", "mine")[0]
    record["content_base64"] = base64.b64encode(png(raw=b"\x00\x00\x00\xff")).decode()
    store.put("console_image", record)
    assert client.get(value["preview_url"]).status_code == 409
    record["content_base64"] = "invalid!"
    store.put("console_image", record)
    assert client.get(value["preview_url"]).status_code == 409
    capabilities = client.get(
        "/api/console/media-capabilities?workspace_id=mine"
    ).json()
    assert capabilities["images"]["pixel_interpretation"] == "unsupported"
    assert capabilities["images"]["max_bytes"] == 1048576
    assert (
        client.get("/api/console/media-capabilities?workspace_id=unknown").status_code
        == 404
    )


@pytest.mark.parametrize(
    "data",
    [
        b"<svg><script>alert(1)</script></svg>",
        png()[:-4],
        png() + b"trailing",
        png()[:20] + b"X" + png()[21:],
        png(width=2049),
        png(width=2048, height=2048),
        png(raw=b"\x00" * 2000000),
        png(raw=b"\x05\xff\x00\x00"),
        png(raw=b"\x00"),
        png(extra=chunk(b"tEXt", b"untrusted metadata")),
        png(extra=chunk(b"acTL", b"animated")),
        png(color=0),
        png()[:8] + chunk(b"IDAT", b"bad") + chunk(b"IEND"),
        png()[:-12] + chunk(b"IDAT", zlib.compress(b"trailing")) + chunk(b"IEND"),
    ],
)
def test_reject_invalid_or_unsupported_without_persistence(api, data):
    client, store = api
    assert upload(client, data).status_code == 422
    assert not store.list("console_attachment", "mine")
    assert not store.list("source", "mine")


def test_request_validation_and_unknown_workspace(api):
    client, _ = api
    body = dict(
        workspace_id="mine",
        name="x.png",
        media_type="image/png",
        content_base64="!invalid",
    )
    assert client.post("/api/console/attachments/image", json=body).status_code == 422
    for name in ("../x.png", "x\\y.png", "x\n.png", ".", ".."):
        body.update(name=name, content_base64=base64.b64encode(png()).decode())
        assert (
            client.post("/api/console/attachments/image", json=body).status_code == 422
        )
    body.update(name="x.png", workspace_id="unknown")
    assert client.post("/api/console/attachments/image", json=body).status_code == 404
    body.update(workspace_id="mine", content_base64="a" * 1400000)
    assert client.post("/api/console/attachments/image", json=body).status_code == 422


def test_rgba_and_multi_idat_accepted(api):
    client, _ = api
    assert upload(client, png(raw=b"\x00\xff\x00\x00\xff", color=6)).status_code == 200
    data = png()
    compressed = zlib.compress(b"\x00\xff\x00\x00")
    data = (
        data[:33]
        + chunk(b"IDAT", compressed[:3])
        + chunk(b"IDAT", compressed[3:])
        + chunk(b"IEND")
    )
    assert upload(client, data).status_code == 200
