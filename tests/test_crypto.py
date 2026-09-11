from Crypto.Cipher import AES

from wechat_emoticon_exporter import crypto


def _pkcs7(data: bytes, block: int = 16) -> bytes:
    pad = block - len(data) % block
    return data + bytes([pad]) * pad


def test_known_key_vector():
    # Regression vector captured from a real account (seed 352428248).
    key = crypto.derive_emoticon_key(352428248, "wxid_yo3vdw8rapa922")
    assert key.hex() == "e5596a6092f5673aa81ad3511fc90b02"


def test_decrypt_round_trip():
    key = bytes(range(16))
    plaintext = b"\x89PNG\r\n\x1a\n" + b"hello world" * 4
    ciphertext = AES.new(key, AES.MODE_CBC, key).encrypt(_pkcs7(plaintext))
    assert crypto.decrypt_cbc(ciphertext, key) == plaintext


def test_decrypt_rejects_bad_length():
    key = bytes(range(16))
    assert crypto.decrypt_cbc(b"short", key) is None
    assert crypto.decrypt_cbc(b"", key) is None


def test_wrong_key_returns_none():
    key = bytes(range(16))
    ciphertext = AES.new(key, AES.MODE_CBC, key).encrypt(_pkcs7(b"x" * 32))
    assert crypto.decrypt_cbc(ciphertext, bytes(16)) is None


def test_detect_format():
    assert crypto.detect_format(b"\x89PNG\r\n\x1a\n") == "png"
    assert crypto.detect_format(b"GIF89a") == "gif"
    assert crypto.detect_format(b"\xff\xd8\xff\xe0") == "jpg"
    assert crypto.detect_format(b"wxgf") == "wxgf"
    assert crypto.detect_format(b"RIFF") == "webp"
    assert crypto.detect_format(b"not an image") is None


def test_verify_key():
    key = bytes(range(16))
    block = AES.new(key, AES.MODE_CBC, key).encrypt(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    assert crypto.verify_key(key, block)
    assert not crypto.verify_key(bytes(16), block)
    assert not crypto.verify_key(key, b"too short")


def test_derive_v2_image_key_shape():
    key = crypto.derive_v2_image_key(352428248, "wxid_yo3vdw8rapa922")
    assert isinstance(key, bytes) and len(key) == 16
