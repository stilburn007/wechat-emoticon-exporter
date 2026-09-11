import sys

import pytest

from wechat_emoticon_exporter import memory


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_list_pids_returns_list():
    assert isinstance(memory.list_pids("definitely-not-a-real-process.exe"), list)


@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows only")
def test_memory_raises_off_windows():
    with pytest.raises(RuntimeError):
        memory.list_pids()
    with pytest.raises(RuntimeError):
        memory.scan_seed_candidates()
