from fastapi import HTTPException, UploadFile

from backend.app.services.workbook_preflight import MAX_FILE_SIZE


async def read_upload_limited(
    file: UploadFile,
    *,
    max_size: int = MAX_FILE_SIZE,
    chunk_size: int = 1024 * 1024,
) -> bytes:
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"工作簿超过 {max_size // 1024 // 1024}MB 限制",
            )
        chunks.append(chunk)
    return b"".join(chunks)
