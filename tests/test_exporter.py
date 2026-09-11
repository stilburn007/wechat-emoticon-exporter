from Crypto.Cipher import AES

from wechat_emoticon_exporter import crypto
from wechat_emoticon_exporter.exporter import probe_ciphertext, resolve_key


def _encrypt(plain: bytes, key: bytes) -> bytes:
    pad = 16 - len(plain) % 16
    return AES.new(key, AES.MODE_CBC, key).encrypt(plain + bytes([pad]) * pad)


def test_resolve_key_with_seed(tmp_path):
    seed, wxid = 123456789, "wxid_test"
    key = crypto.derive_emoticon_key(seed, wxid)
    plain = b"\x89PNG\r\n\x1a\n" + b"A" * 24

    persist = tmp_path / "Persist"
    persist.mkdir()
    (persist / "abc").write_bytes(_encrypt(plain, key))

    assert probe_ciphertext(str(tmp_path)) is not None
    resolved_seed, resolved_key = resolve_key(
        str(tmp_path), [wxid], seed=seed, log=lambda *_: None
    )
    assert resolved_seed == seed
    assert resolved_key == key


def test_probe_missing_dir(tmp_path):
    assert probe_ciphertext(str(tmp_path)) is None
