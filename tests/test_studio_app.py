from __future__ import annotations

import io
import os
import sys
import zipfile
from pathlib import Path

import pytest
from Crypto.Cipher import AES
from PIL import Image

from backend import core_bridge, library
from backend.app import _progress_from_message, create_app


def make_client(tmp_path: Path):
    app = create_app(str(tmp_path / "studio-data"))
    app.config.update(TESTING=True)
    return app, app.test_client()


def test_health_and_demo_library(tmp_path: Path):
    _app, client = make_client(tmp_path)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.get_json()["name"] == "WeChat Emoticon Studio"

    response = client.post("/api/demo")
    assert response.status_code == 201
    library = response.get_json()["library"]
    assert library["total"] == 9
    assert library["animated"] == 6
    assert len(library["items"]) == library["total"]


def test_preview_speed_variant(tmp_path: Path):
    _app, client = make_client(tmp_path)
    library = client.post("/api/demo").get_json()["library"]
    animated = next(item for item in library["items"] if item["animated"])

    response = client.get(
        f"/api/libraries/{library['id']}/items/{animated['id']}/content?speed=1.37"
    )
    assert response.status_code == 200
    assert response.mimetype == "image/gif"
    with Image.open(io.BytesIO(response.data)) as image:
        assert image.n_frames > 1


def test_archive_and_folder_export(tmp_path: Path):
    _app, client = make_client(tmp_path)
    library = client.post("/api/demo").get_json()["library"]
    ids = [item["id"] for item in library["items"][:3]]

    archive = client.post(
        f"/api/libraries/{library['id']}/archive",
        json={"item_ids": ids, "speed": 1.5},
    )
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.data)) as bundle:
        assert len(bundle.namelist()) == 3

    target = tmp_path / "saved"
    exported = client.post(
        f"/api/libraries/{library['id']}/export",
        json={
            "item_ids": ids,
            "speed": 1,
            "target_dir": str(target),
            "preserve_groups": True,
        },
    )
    assert exported.status_code == 200
    assert exported.get_json()["count"] == 3
    assert len(list(target.rglob("*.*"))) == 3


def test_save_current_configuration_to_file(tmp_path: Path):
    _app, client = make_client(tmp_path)
    library = client.post("/api/demo").get_json()["library"]
    animated = next(item for item in library["items"] if item["animated"])
    target = tmp_path / "saved-current.gif"

    response = client.post(
        f"/api/libraries/{library['id']}/items/{animated['id']}/save",
        json={"target_file": str(target), "speed": 1.37},
    )
    assert response.status_code == 200
    assert response.get_json()["speed"] == 1.37
    assert target.is_file()
    with Image.open(target) as image:
        assert image.n_frames > 1


def test_library_delete(tmp_path: Path):
    app, client = make_client(tmp_path)
    library = client.post("/api/demo").get_json()["library"]
    root = Path(app.extensions["studio_state"].get_library(library["id"]).root)
    assert root.exists()

    response = client.delete(f"/api/libraries/{library['id']}")
    assert response.status_code == 200
    assert not root.exists()


def test_key_resolution_skips_unusable_first_file(tmp_path: Path, monkeypatch):
    seed = 123456789
    wxid = "wxid_test"
    emoticon = tmp_path / "business" / "emoticon"
    first = emoticon / "Persist" / "00" / "first"
    second = emoticon / "Persist" / "01" / "second"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b"not-an-encrypted-emoticon")

    key = core_bridge.crypto.derive_emoticon_key(seed, wxid)
    plaintext = b"\x89PNG\r\n\x1a\n" + b"A" * 24
    padding = 16 - len(plaintext) % 16
    second.write_bytes(
        AES.new(key, AES.MODE_CBC, key).encrypt(plaintext + bytes([padding]) * padding)
    )

    monkeypatch.setattr(core_bridge.memory, "scan_seed_candidates", lambda: {seed})
    account = core_bridge.locate.Account(
        folder=str(tmp_path),
        wxid=wxid,
        folder_name=wxid,
    )
    resolved_seed, resolved_key = core_bridge.resolve_account_key(
        account,
        str(emoticon),
        log=lambda _message: None,
    )
    assert resolved_seed == seed
    assert resolved_key == key


def test_key_resolution_rejects_single_unpadded_match(tmp_path: Path):
    seed = 987654321
    wxid = "wxid_test"
    emoticon = tmp_path / "business" / "emoticon"
    target = emoticon / "Persist" / "00" / "partial"
    target.parent.mkdir(parents=True)

    key = core_bridge.crypto.derive_emoticon_key(seed, wxid)
    first_block = b"\x89PNG\r\n\x1a\n12345678"
    target.write_bytes(AES.new(key, AES.MODE_CBC, key).encrypt(first_block))

    account = core_bridge.locate.Account(
        folder=str(tmp_path),
        wxid=wxid,
        folder_name=wxid,
    )
    with pytest.raises(RuntimeError, match="Seed"):
        core_bridge.resolve_account_key(
            account,
            str(emoticon),
            seed=seed,
            log=lambda _message: None,
        )


def test_recent_account_is_listed_first(tmp_path: Path, monkeypatch):
    older = tmp_path / "wxid_older_0001"
    newer = tmp_path / "wxid_newer_0002"
    for account in (older, newer):
        (account / "db_storage").mkdir(parents=True)
        (account / "business" / "emoticon").mkdir(parents=True)
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    monkeypatch.setattr(core_bridge.locate, "find_data_roots", lambda _extra=None: [str(tmp_path)])
    _roots, accounts = core_bridge.discover_accounts([str(tmp_path)])
    assert [account.wxid for account in accounts] == ["wxid_newer", "wxid_older"]


def test_discovery_keeps_account_without_emoticon_directory(tmp_path: Path, monkeypatch):
    account = tmp_path / "wxid_test_0001"
    (account / "db_storage").mkdir(parents=True)

    monkeypatch.setattr(core_bridge.locate, "find_data_roots", lambda _extra=None: [str(tmp_path)])
    _roots, accounts = core_bridge.discover_accounts([str(tmp_path)])
    assert len(accounts) == 1
    assert core_bridge.account_to_dict(accounts[0])["has_emoticon"] is False


def test_ffmpeg_subprocess_is_hidden_on_windows(tmp_path: Path, monkeypatch):
    target = tmp_path / "preview.gif"
    observed: dict[str, object] = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed.update(kwargs)
        target.write_bytes(b"x" * 101)
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(core_bridge.subprocess, "run", fake_run)
    assert core_bridge._run_ffmpeg_hidden(
        "ffmpeg",
        "source.h265",
        str(target),
        10,
        input_format="hevc",
    )
    command = observed["command"]
    assert command[command.index("-i") - 2 : command.index("-i")] == ["-f", "hevc"]
    if sys.platform == "win32":
        assert observed["creationflags"] == getattr(
            core_bridge.subprocess,
            "CREATE_NO_WINDOW",
            0x08000000,
        )


def test_wxgf_conversion_reports_per_file_progress():
    assert _progress_from_message("[progress] wxgf 1/10 file.wxgf") == 74
    assert _progress_from_message("[progress] wxgf 10/10 file.wxgf") == 92


def test_speed_variant_uses_short_temporary_filename(tmp_path: Path, monkeypatch):
    root = tmp_path / "cache"
    source = root / "Persist" / "source.gif"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"GIF89a")
    item = library.EmoticonItem(
        id="item",
        name="source.gif",
        path=str(source),
        relative_path="Persist/source.gif",
        group="Persist",
        category="original",
        extension=".gif",
        mime_type="image/gif",
        size=source.stat().st_size,
        modified_at=source.stat().st_mtime,
        animated=True,
    )
    emoticon_library = library.EmoticonLibrary(
        id="library",
        account="test",
        wxid="wxid_test",
        root=str(root),
        created_at=0,
        items=[item],
    )
    observed: dict[str, str] = {}

    def fake_adjust(_source, target, _speed):
        observed["name"] = Path(target).name
        Path(target).write_bytes(b"GIF89a")

    monkeypatch.setattr(library, "_adjust_gif_speed", fake_adjust)
    assert emoticon_library.variant_path(item, 0.6).suffix == ".gif"
    assert observed["name"].startswith("t-")
    assert len(observed["name"]) < 24


def test_account_display_name_uses_cached_wechat_nickname(tmp_path: Path, monkeypatch):
    folder = tmp_path / "wxid_test_0001"
    folder.mkdir()
    account = core_bridge.locate.Account(
        folder=str(folder),
        wxid="wxid_test",
        folder_name="wxid_test_0001",
    )
    monkeypatch.setitem(core_bridge._DISPLAY_NAME_CACHE, "wxid_test", "TestUser")
    assert core_bridge.account_display_name(account) == "TestUser"
    assert core_bridge.account_to_dict(account)["display_name"] == "TestUser"


def test_job_logs_are_incremental_and_keys_are_cached(tmp_path: Path):
    app = create_app(str(tmp_path / "studio-data"))
    state = app.extensions["studio_state"]
    job = state.add_job("scan")
    state.log_job(job, "第一条日志", progress=10)
    state.log_job(job, "第二条日志", level="error", progress=20)

    first_page = job.to_dict(0)
    second_page = job.to_dict(first_page["next_log_index"])
    assert [entry["message"] for entry in first_page["logs"]] == ["第一条日志", "第二条日志"]
    assert second_page["logs"] == []

    state.set_cached_key("wxid_test", "0123456789abcdef0123456789abcdef")
    assert state.get_cached_key("wxid_test") == "0123456789abcdef0123456789abcdef"


def test_key_failure_message_is_actionable(tmp_path: Path):
    account = core_bridge.locate.Account(
        folder=str(tmp_path / "wxid_test_0001"),
        wxid="wxid_test",
        folder_name="wxid_test_0001",
    )
    message = core_bridge.humanize_error(
        "Could not recover a consistent key for wxid_test_0001.",
        account,
    )
    assert "最近使用" in message
    assert "Seed" in message
