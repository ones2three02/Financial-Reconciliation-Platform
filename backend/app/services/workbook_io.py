import re
from io import BytesIO
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook


_AUTOFILTER_BLOCK = re.compile(rb"<autoFilter\b.*?</autoFilter>", re.DOTALL)
_AUTOFILTER_EMPTY = re.compile(rb"<autoFilter\b[^>]*/>")
MAX_ARCHIVE_ENTRIES = 10_000
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024
MAX_ENTRY_COMPRESSION_RATIO = 100


class WorkbookArchiveLimitError(ValueError):
    """工作簿压缩包超过安全资源边界。"""


def _validate_archive(input_zip: ZipFile) -> None:
    entries = input_zip.infolist()
    if len(entries) > MAX_ARCHIVE_ENTRIES:
        raise WorkbookArchiveLimitError("工作簿压缩条目数量超过安全限制")
    total_uncompressed = sum(info.file_size for info in entries)
    if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
        raise WorkbookArchiveLimitError("工作簿解压后大小超过安全限制")
    for info in entries:
        if info.file_size == 0:
            continue
        ratio = info.file_size / max(info.compress_size, 1)
        if ratio > MAX_ENTRY_COMPRESSION_RATIO:
            raise WorkbookArchiveLimitError("工作簿压缩比超过安全限制")


def _without_worksheet_filters(content: bytes) -> bytes:
    """移除不参与提取的筛选器元数据，兼容第三方导出的非标准筛选值。"""
    source = BytesIO(content)
    output = BytesIO()
    with ZipFile(source, "r") as input_zip, ZipFile(
        output,
        "w",
        compression=ZIP_DEFLATED,
    ) as output_zip:
        _validate_archive(input_zip)
        for info in input_zip.infolist():
            payload = input_zip.read(info.filename)
            if info.filename.startswith("xl/worksheets/") and info.filename.endswith(".xml"):
                payload = _AUTOFILTER_BLOCK.sub(b"", payload)
                payload = _AUTOFILTER_EMPTY.sub(b"", payload)
            output_zip.writestr(info, payload)
    return output.getvalue()


def load_data_workbook(content: bytes):
    """以只读、公式结果模式打开工作簿，筛选器不影响任何业务数据。"""
    try:
        sanitized = _without_worksheet_filters(content)
    except BadZipFile:
        sanitized = content
    return load_workbook(BytesIO(sanitized), read_only=True, data_only=True)
