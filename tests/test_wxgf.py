from wechat_emoticon_exporter import wxgf


def test_first_nal_finds_vps():
    data = b"\x00\x00\x00\x01\x40\x01rest"
    assert wxgf._first_nal(data) == 0


def test_first_nal_none():
    assert wxgf._first_nal(b"no nal marker here") is None


def test_find_ffmpeg_type():
    result = wxgf.find_ffmpeg()
    assert result is None or isinstance(result, str)
