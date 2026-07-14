import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from backend.app.api.upload_utils import read_upload_limited


def test_upload_reader_stops_when_limit_is_exceeded():
    upload = UploadFile(filename="oversized.xlsx", file=BytesIO(b"x" * 11))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(read_upload_limited(upload, max_size=10, chunk_size=4))

    assert exc_info.value.status_code == 413


def test_upload_reader_returns_content_within_limit():
    upload = UploadFile(filename="safe.xlsx", file=BytesIO(b"safe"))

    assert asyncio.run(read_upload_limited(upload, max_size=10, chunk_size=4)) == b"safe"
