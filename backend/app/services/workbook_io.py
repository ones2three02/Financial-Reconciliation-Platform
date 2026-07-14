import re
from io import BytesIO
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook


_AUTOFILTER_BLOCK = re.compile(rb"<autoFilter\b.*?</autoFilter>", re.DOTALL)
_AUTOFILTER_EMPTY = re.compile(rb"<autoFilter\b[^>]*/>")


def _without_worksheet_filters(content: bytes) -> bytes:
    """移除不参与提取的筛选器元数据，兼容第三方导出的非标准筛选值。"""
    source = BytesIO(content)
    output = BytesIO()
    with ZipFile(source, "r") as input_zip, ZipFile(
        output,
        "w",
        compression=ZIP_DEFLATED,
    ) as output_zip:
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
