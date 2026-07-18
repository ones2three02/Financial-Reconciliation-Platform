import re
from io import BytesIO
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook


_AUTOFILTER_BLOCK = re.compile(rb"<autoFilter\b.*?</autoFilter>", re.DOTALL)
_AUTOFILTER_EMPTY = re.compile(rb"<autoFilter\b[^>]*/>")
_DIMENSION_BLOCK = re.compile(rb"<dimension\b[^>]*>")
MAX_ARCHIVE_ENTRIES = 10_000
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024
MAX_ENTRY_COMPRESSION_RATIO = 100


class WorkbookArchiveLimitError(ValueError):
    """工作簿压缩包超过安全资源边界。"""


class DecryptionError(ValueError):
    """解密相关的错误。"""
    pass


class PasswordRequiredError(DecryptionError):
    """需要输入密码。"""
    pass


class InvalidPasswordError(DecryptionError):
    """密码错误。"""
    pass


def is_excel_encrypted(content: bytes) -> bool:
    """检查是否包含 OLE 复合文档头，加密的 .xlsx 通常存放在 OLE 容器中。"""
    return content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


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
                payload = _DIMENSION_BLOCK.sub(b"", payload)
            output_zip.writestr(info, payload)
    return output.getvalue()


def load_data_workbook(content: bytes, password: str | None = None):
    """以只读、公式结果模式打开工作簿，支持对加密文件进行动态解密。"""
    if is_excel_encrypted(content):
        if not password:
            raise PasswordRequiredError("PASSWORD_REQUIRED")
        try:
            import msoffcrypto
        except ImportError:
            raise DecryptionError("系统缺失加密文件解密模块，请安装 msoffcrypto-tool")
        try:
            decrypted = BytesIO()
            office_file = msoffcrypto.OfficeFile(BytesIO(content))
            office_file.load_key(password=password)
            office_file.decrypt(decrypted)
            content = decrypted.getvalue()
        except Exception as exc:
            raise InvalidPasswordError("INVALID_PASSWORD") from exc

    try:
        sanitized = _without_worksheet_filters(content)
    except BadZipFile:
        sanitized = content
    return load_workbook(BytesIO(sanitized), read_only=True, data_only=True)
