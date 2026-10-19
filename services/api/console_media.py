"""Bounded PNG attachments. Pixels are previewable, never claimed as model vision.

Deliberately supports only PNG 8-bit RGB/RGBA without metadata or interlacing.
This is a container/scanline validator, not a general image conversion service.
"""

import base64
import binascii
import hashlib
import struct
import zlib
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from services.api.store import now, uid
from services.worker.data_tools import create_source


MAX_BYTES = 1024 * 1024
SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ImageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    name: str = Field(min_length=1, max_length=200)
    media_type: Literal["image/png"]
    content_base64: str = Field(min_length=1, max_length=4 * ((MAX_BYTES + 2) // 3))


def validate_png(data):
    """Reject malformed, oversized and unsupported containers before browser decoding."""
    if not data.startswith(SIGNATURE) or len(data) > MAX_BYTES:
        raise ValueError("Requires PNG at most 1 MiB")
    offset, chunks, compressed = 8, [], bytearray()
    width = height = channels = None
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError("Truncated PNG chunk")
        size = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError("Truncated PNG payload")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ValueError("Invalid PNG CRC")
        if kind == b"IHDR":
            if chunks or size != 13:
                raise ValueError("PNG requires one leading IHDR")
            width, height, depth, color, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", payload)
            )
            if not (
                1 <= width <= 2048 and 1 <= height <= 2048 and width * height <= 1048576
            ):
                raise ValueError("PNG dimensions exceed 2048 per side or 1M pixels")
            if (
                depth != 8
                or color not in (2, 6)
                or compression
                or filtering
                or interlace
            ):
                raise ValueError("Only non-interlaced 8-bit RGB/RGBA PNG supported")
            channels = 3 if color == 2 else 4
        elif kind == b"IDAT":
            if not chunks or chunks[-1] not in (b"IHDR", b"IDAT"):
                raise ValueError("PNG IDAT must follow IHDR")
            compressed.extend(payload)
        elif kind == b"IEND":
            if not chunks or chunks[-1] != b"IDAT" or size or end != len(data):
                raise ValueError("PNG requires final empty IEND")
        else:
            raise ValueError(
                "PNG metadata, animation and extra chunks are unsupported; export plain RGB/RGBA PNG"
            )
        chunks.append(kind)
        offset = end
    if not chunks or chunks[-1] != b"IEND":
        raise ValueError("PNG missing IEND")
    expected = height * (1 + width * channels)
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(bytes(compressed), expected + 1)
    except zlib.error:
        raise ValueError("Invalid PNG compressed pixels") from None
    if (
        len(raw) != expected
        or not decoder.eof
        or decoder.unused_data
        or decoder.unconsumed_tail
    ):
        raise ValueError("PNG scanline size mismatch or invalid compressed stream")
    if any(raw[i] > 4 for i in range(0, expected, 1 + width * channels)):
        raise ValueError("Invalid PNG scanline filter")
    return width, height


def create_console_media_router(app):
    router = APIRouter(prefix="/api/console")

    @router.get("/media-capabilities")
    def capabilities(workspace_id: str):
        if not app.state.store.get("workspace", workspace_id):
            raise HTTPException(404, "Workspace not found")
        return dict(
            images=dict(
                state="healthy",
                media_types=["image/png"],
                subset="8-bit RGB/RGBA; non-interlaced; IHDR/IDAT/IEND only; no metadata/animation",
                max_bytes=MAX_BYTES,
                max_dimension=2048,
                max_pixels=1048576,
                pixel_interpretation="unsupported",
                reason="Local upload and preview only; no OCR or model vision adapter",
            )
        )

    @router.post("/attachments/image")
    def upload(body: ImageInput):
        if any(
            c in body.name for c in ("/", "\\", "\x00", "\r", "\n")
        ) or body.name in (".", ".."):
            raise HTTPException(422, "Attachment requires a plain filename")
        try:
            data = base64.b64decode(body.content_base64, validate=True)
            width, height = validate_png(data)
        except (ValueError, binascii.Error) as exc:
            raise HTTPException(422, str(exc)) from None
        store = app.state.store
        with store.lock:
            if not store.get("workspace", body.workspace_id):
                raise HTTPException(404, "Workspace not found")
            attachment_id = uid()
            sha256 = hashlib.sha256(data).hexdigest()
            source = create_source(
                store,
                body.workspace_id,
                body.name,
                (
                    "UNTRUSTED IMAGE ATTACHMENT METADATA ONLY. Image pixels not interpreted: "
                    "no vision adapter is available. Do not describe, OCR or infer image contents.\n"
                    f"Name: {body.name}\nType: image/png\nSize: {len(data)} bytes\n"
                    f"Dimensions: {width}x{height}\nSHA256: {sha256}"
                ),
                "text/plain",
            )
            value = dict(
                id=attachment_id,
                workspace_id=body.workspace_id,
                source_id=source["id"],
                name=body.name,
                media_type="image/png",
                size=len(data),
                sha256=sha256,
                width=width,
                height=height,
                pixel_interpretation="unsupported",
                created_at=now(),
                preview_url=f"/api/console/attachments/{attachment_id}/image?"
                + urlencode(dict(workspace_id=body.workspace_id)),
            )
            image = dict(
                id=uid(),
                workspace_id=body.workspace_id,
                attachment_id=attachment_id,
                content_base64=body.content_base64,
            )
            audit = dict(
                id=uid(),
                workspace_id=body.workspace_id,
                actor="local-operator",
                action="attachment.image.created",
                target_id=attachment_id,
                outcome="success",
                created_at=now(),
            )
            store.put_many(
                [
                    ("console_attachment", value),
                    ("console_image", image),
                    ("audit", audit),
                ]
            )
            store.event(
                body.workspace_id,
                "console.attachment.image.created",
                dict(target_id=attachment_id),
            )
            return value

    @router.get("/attachments/{attachment_id}/image")
    def preview(attachment_id: str, workspace_id: str):
        store = app.state.store
        with store.lock:
            attachment = store.get("console_attachment", attachment_id)
            if (
                not attachment
                or attachment.get("workspace_id") != workspace_id
                or attachment.get("media_type") != "image/png"
            ):
                raise HTTPException(404, "Image not found in workspace")
            record = next(
                (
                    item
                    for item in store.list("console_image", workspace_id)
                    if item.get("attachment_id") == attachment_id
                ),
                None,
            )
            if not record:
                raise HTTPException(404, "Image not found in workspace")
            try:
                data = base64.b64decode(record["content_base64"], validate=True)
            except (ValueError, binascii.Error, KeyError, TypeError):
                raise HTTPException(
                    409, "Stored image integrity check failed"
                ) from None
            if hashlib.sha256(data).hexdigest() != attachment["sha256"]:
                raise HTTPException(409, "Stored image integrity check failed")
            return Response(
                data,
                media_type="image/png",
                headers={
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "no-store",
                    "Content-Security-Policy": "default-src 'none'; sandbox",
                    "Content-Disposition": 'inline; filename="attachment.png"',
                },
            )

    return router
