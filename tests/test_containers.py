import struct

from wechat_emoticon_exporter.containers import split_container


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + chunk_type + data + b"\x00\x00\x00\x00"


def make_png() -> bytes:
    ihdr = _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    iend = _png_chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + iend


def make_gif() -> bytes:
    header = b"GIF89a"
    screen_descriptor = struct.pack("<HHBBB", 1, 1, 0, 0, 0)
    comment = b"\x21\xfe\x03abc\x00"
    return header + screen_descriptor + comment + b"\x3b"


def make_jpeg() -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    return b"\xff\xd8" + app0 + b"\xff\xd9"


def test_split_three_formats():
    parts = split_container(make_png() + make_gif() + make_jpeg())
    assert len(parts) == 3
    assert parts[0].startswith(b"\x89PNG")
    assert parts[1].startswith(b"GIF89a")
    assert parts[2].startswith(b"\xff\xd8")


def test_split_repeated_png():
    parts = split_container(make_png() + make_png())
    assert len(parts) == 2


def test_split_empty_and_garbage():
    assert split_container(b"") == []
    assert split_container(b"not an image at all") == []
