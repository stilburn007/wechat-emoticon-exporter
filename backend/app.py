"""Flask application and JSON API for WeChat Emoticon Studio."""

from __future__ import annotations

import atexit
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.exceptions import HTTPException

from wechat_emoticon_exporter import __version__

from . import core_bridge
from .demo import build_demo_library
from .library import SPEED_MAX, SPEED_MIN, EmoticonLibrary, build_library, copy_item_to


def _frontend_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "frontend"
    return Path(__file__).resolve().parents[1] / "frontend"


def _default_data_dir() -> Path:
    override = os.environ.get("WECHAT_EMOTICON_STUDIO_HOME")
    if override:
        return Path(override).expanduser().resolve()
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "WeChatEmoticonStudio"
    return Path.home() / ".wechat-emoticon-studio"


@dataclass
class ScanJob:
    id: str
    kind: str
    status: str = "queued"
    progress: int = 0
    message: str = "Queued"
    created_at: float = field(default_factory=time.time)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    logs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, after_log: int = 0) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "logs": self.logs[after_log:],
            "next_log_index": len(self.logs),
        }


class AppState:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        runtime_root = Path(tempfile.gettempdir()) / "WeChatEmoticonStudio"
        self.runtime_dir = runtime_root / uuid.uuid4().hex
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.libraries: dict[str, EmoticonLibrary] = {}
        self.jobs: dict[str, ScanJob] = {}
        self.allowed_export_dirs: set[str] = set()
        self.lock = threading.RLock()
        self.key_cache_path = self.data_dir / "account_keys.json"

    def add_library(self, library: EmoticonLibrary) -> None:
        with self.lock:
            self.libraries[library.id] = library

    def add_job(self, kind: str) -> ScanJob:
        job = ScanJob(id=uuid.uuid4().hex, kind=kind)
        with self.lock:
            self.jobs[job.id] = job
        return job

    def update_job(self, job: ScanJob, **changes: Any) -> None:
        with self.lock:
            for key, value in changes.items():
                setattr(job, key, value)

    def log_job(
        self,
        job: ScanJob,
        message: str,
        *,
        level: str = "info",
        progress: Optional[int] = None,
    ) -> None:
        with self.lock:
            job.logs.append(
                {
                    "time": time.strftime("%H:%M:%S"),
                    "level": level,
                    "message": message,
                }
            )
            job.message = message
            if progress is not None:
                job.progress = max(job.progress, min(100, int(progress)))

    def get_cached_key(self, wxid: str) -> Optional[str]:
        with self.lock:
            try:
                values = json.loads(self.key_cache_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            value = values.get(wxid) if isinstance(values, dict) else None
            return value if isinstance(value, str) and len(value) == 32 else None

    def set_cached_key(self, wxid: str, key_hex: Optional[str]) -> None:
        if not key_hex:
            return
        with self.lock:
            try:
                values = json.loads(self.key_cache_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                values = {}
            if not isinstance(values, dict):
                values = {}
            values[wxid] = key_hex
            temporary = self.key_cache_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(values, indent=2), encoding="utf-8")
            os.replace(temporary, self.key_cache_path)

    def get_library(self, library_id: str) -> EmoticonLibrary:
        with self.lock:
            library = self.libraries.get(library_id)
        if library is None:
            raise KeyError("Library not found.")
        return library

    def cleanup(self) -> None:
        shutil.rmtree(self.runtime_dir, ignore_errors=True)


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _validated_ids(payload: dict[str, Any], library: EmoticonLibrary) -> list[str]:
    ids = payload.get("item_ids")
    if not isinstance(ids, list) or not ids:
        raise ValueError("Select at least one emoticon.")
    item_map = library.item_map()
    valid = [item_id for item_id in ids if item_id in item_map]
    if not valid:
        raise ValueError("No valid emoticons were selected.")
    return list(dict.fromkeys(valid))


def _progress_from_message(message: str) -> int:
    if "scanning Weixin.exe" in message:
        return 10
    if "candidate" in message:
        return 22
    if "credentials verified" in message:
        return 34
    for index, group in enumerate(("Persist", "PersistStore", "Thumb", "ThumbStore", "Temp")):
        if message.startswith(f"[*] {group}:"):
            return 44 + index * 7
    if message.startswith("[progress] wxgf "):
        try:
            current, total = message.split()[2].split("/", 1)
            return 72 + round(20 * int(current) / max(1, int(total)))
        except (IndexError, ValueError):
            return 72
    if "named" in message:
        return 70
    if "wxgf -> gif" in message:
        return 94
    return 0


def create_app(data_dir: Optional[str] = None) -> Flask:
    frontend = _frontend_dir()
    app = Flask(__name__, static_folder=str(frontend), static_url_path="/static")
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
    state = AppState(data_dir or str(_default_data_dir()))
    app.extensions["studio_state"] = state
    atexit.register(state.cleanup)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            return _json_error(error.description or error.name, error.code or 500)
        if isinstance(error, (ValueError, RuntimeError, KeyError)):
            return _json_error(str(error), 400 if not isinstance(error, KeyError) else 404)
        try:
            state.data_dir.mkdir(parents=True, exist_ok=True)
            with open(state.data_dir / "studio-errors.log", "a", encoding="utf-8") as handle:
                handle.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.path}\n")
                handle.write(traceback.format_exc())
        except OSError:
            pass
        app.logger.exception("Unhandled request error")
        return _json_error("The operation failed unexpectedly.", 500)

    @app.get("/favicon.ico")
    def favicon():
        return "", 204

    @app.get("/")
    def index():
        return send_from_directory(frontend, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "name": "WeChat Emoticon Studio",
                "version": __version__,
                **core_bridge.runtime_info(),
            }
        )

    @app.get("/api/accounts")
    def accounts():
        roots, found = core_bridge.discover_accounts(request.args.getlist("data_root"))
        return jsonify(
            {
                "roots": roots,
                "accounts": [core_bridge.account_to_dict(account) for account in found],
            }
        )

    @app.post("/api/demo")
    def demo():
        library = build_demo_library(str(state.runtime_dir))
        state.add_library(library)
        return jsonify({"library": library.to_dict()}), 201

    @app.post("/api/scan")
    def scan():
        payload = request.get_json(silent=True) or {}
        account_name = str(payload.get("account") or "").strip()
        if not account_name:
            raise ValueError("Choose a WeChat account first.")

        extra_roots = payload.get("data_roots")
        if isinstance(extra_roots, str):
            extra_roots = [extra_roots]
        if not isinstance(extra_roots, list):
            extra_roots = []

        _roots, found = core_bridge.discover_accounts(extra_roots)
        account = core_bridge.select_account(found, account_name)
        seed = payload.get("seed")
        if seed in ("", None):
            seed = None
        else:
            seed = int(seed)
        key_hex = str(payload.get("key") or "").strip() or None
        if key_hex is not None and (len(key_hex) != 32 or any(c not in "0123456789abcdefABCDEF" for c in key_hex)):
            raise ValueError("The key must be exactly 32 hexadecimal characters.")

        job = state.add_job("scan")
        output_dir = state.runtime_dir / f"library-{job.id}"
        display_name = core_bridge.account_display_name(account)

        def run_scan() -> None:
            state.update_job(job, status="running", progress=4, message="正在准备读取")
            state.log_job(job, f"开始读取账号「{display_name}」", progress=4)
            state.log_job(job, f"账号目录：{account.folder}", progress=5)
            stop_monitor = threading.Event()
            monitor_wakeup = threading.Event()
            monitor_state = {"count": 0}

            def monitor_output() -> None:
                while not stop_monitor.is_set():
                    monitor_wakeup.wait(0.35)
                    monitor_wakeup.clear()
                    if stop_monitor.is_set():
                        break
                    if not output_dir.is_dir():
                        continue
                    try:
                        partial = build_library(
                            str(output_dir),
                            display_name,
                            account.wxid,
                            library_id=job.id,
                            created_at=job.created_at,
                        )
                    except Exception:
                        continue
                    if not partial.items:
                        continue
                    state.update_job(job, result={"library": partial.to_dict()})
                    if len(partial.items) != monitor_state["count"]:
                        monitor_state["count"] = len(partial.items)
                        state.log_job(
                            job,
                            f"已读取到 {monitor_state['count']} 个表情，界面正在实时更新",
                        )

            try:
                monitor_thread = threading.Thread(
                    target=monitor_output,
                    daemon=True,
                    name=f"catalog-{job.id}",
                )
                monitor_thread.start()

                def forward(message: str) -> None:
                    progress = _progress_from_message(message) or job.progress
                    state.log_job(
                        job,
                        core_bridge.safe_log(message),
                        progress=progress,
                    )

                def perform_scan(override_key: Optional[str] = None):
                    return core_bridge.scan_account(
                        account,
                        str(output_dir),
                        seed=seed,
                        key_hex=override_key if override_key is not None else key_hex,
                        name_from_db=bool(payload.get("name_from_db")),
                        log=forward,
                        on_file_written=lambda _path: monitor_wakeup.set(),
                    )

                cached_key = state.get_cached_key(account.wxid)
                if key_hex is None and seed is None and cached_key:
                    state.log_job(job, "检测到本机保存的上次密钥，优先尝试使用", level="info")
                    try:
                        result = perform_scan(cached_key)
                    except RuntimeError:
                        state.log_job(
                            job,
                            "上次保存的密钥已失效，继续扫描当前微信进程内存",
                            level="warning",
                        )
                        result = perform_scan()
                else:
                    result = perform_scan()
                if result.total_files <= 0:
                    raise RuntimeError(
                        f"账号「{display_name}」没有解出任何表情，请确认微信已登录并重新选择当前账号。"
                    )
                stop_monitor.set()
                monitor_thread.join(timeout=2)
                state.log_job(job, "正在生成最终表情目录", progress=95)
                library = build_library(
                    str(output_dir),
                    display_name,
                    account.wxid,
                    library_id=job.id,
                    created_at=job.created_at,
                )
                if not library.items:
                    raise RuntimeError(f"账号「{display_name}」读取完成，但没有生成可预览的表情。")
                state.add_library(library)
                state.set_cached_key(account.wxid, result.key)
                state.update_job(
                    job,
                    status="complete",
                    progress=100,
                    message=f"读取完成，共 {len(library.items)} 个表情",
                    result={"library": library.to_dict()},
                )
                state.log_job(
                    job,
                    f"读取完成，共 {len(library.items)} 个表情",
                    level="success",
                    progress=100,
                )
            except Exception as error:
                stop_monitor.set()
                shutil.rmtree(output_dir, ignore_errors=True)
                human_message = core_bridge.humanize_error(error, account)
                state.log_job(job, human_message, level="error", progress=100)
                state.update_job(
                    job,
                    status="failed",
                    message="读取失败",
                    error=human_message,
                )

        threading.Thread(target=run_scan, daemon=True, name=f"scan-{job.id}").start()
        return jsonify({"job": job.to_dict()}), 202

    @app.get("/api/jobs/<job_id>")
    def job_status(job_id: str):
        with state.lock:
            job = state.jobs.get(job_id)
        if job is None:
            return _json_error("Job not found.", 404)
        after_log = max(0, request.args.get("after", 0, type=int))
        return jsonify({"job": job.to_dict(after_log)})

    @app.get("/api/libraries/<library_id>")
    def library_detail(library_id: str):
        library = state.get_library(library_id)
        return jsonify({"library": library.to_dict()})

    @app.get("/api/libraries/<library_id>/items/<item_id>/content")
    def item_content(library_id: str, item_id: str):
        library = state.get_library(library_id)
        item = library.item_map().get(item_id)
        if item is None:
            return _json_error("Emoticon not found.", 404)
        if not item.previewable:
            return _json_error("This raw WXGF file cannot be previewed in the browser.", 415)
        speed = request.args.get("speed", 1.0, type=float)
        variant = library.variant_path(item, speed)
        return send_file(
            variant,
            mimetype=item.mime_type if variant.suffix == item.extension else "image/gif",
            conditional=True,
            download_name=item.name,
            as_attachment=request.args.get("download") == "1",
        )

    @app.post("/api/libraries/<library_id>/items/<item_id>/save")
    def save_item(library_id: str, item_id: str):
        library = state.get_library(library_id)
        item = library.item_map().get(item_id)
        if item is None:
            return _json_error("Emoticon not found.", 404)
        payload = request.get_json(silent=True) or {}
        target_text = str(payload.get("target_file") or "").strip()
        if not target_text:
            raise ValueError("Choose a destination file.")
        target = Path(os.path.expandvars(target_text)).expanduser()
        if not target.is_absolute():
            raise ValueError("The destination must be an absolute file path.")
        speed = max(SPEED_MIN, min(SPEED_MAX, float(payload.get("speed") or 1.0)))
        source = library.variant_path(item, speed)
        if not target.suffix:
            target = target.with_suffix(source.suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return jsonify({"saved": str(target.resolve()), "speed": speed})

    @app.post("/api/libraries/<library_id>/archive")
    def archive(library_id: str):
        library = state.get_library(library_id)
        payload = request.get_json(silent=True) or {}
        item_ids = _validated_ids(payload, library)
        speed = max(SPEED_MIN, min(SPEED_MAX, float(payload.get("speed") or 1.0)))
        item_map = library.item_map()
        archive_name = f"wechat-emoticons-{int(time.time())}.zip"
        archive_path = state.runtime_dir / archive_name
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            used_names: set[str] = set()
            for item_id in item_ids:
                item = item_map[item_id]
                source = library.variant_path(item, speed)
                base = item.name
                stem, suffix = os.path.splitext(base)
                candidate = base
                index = 2
                while candidate.casefold() in used_names:
                    candidate = f"{stem}_{index}{suffix}"
                    index += 1
                used_names.add(candidate.casefold())
                bundle.write(source, candidate)
        return send_file(archive_path, mimetype="application/zip", as_attachment=True, download_name=archive_name)

    @app.post("/api/libraries/<library_id>/export")
    def export_to_folder(library_id: str):
        library = state.get_library(library_id)
        payload = request.get_json(silent=True) or {}
        item_ids = _validated_ids(payload, library)
        target_text = str(payload.get("target_dir") or "").strip()
        if not target_text:
            raise ValueError("Enter an output folder.")
        target = Path(os.path.expandvars(target_text)).expanduser()
        if not target.is_absolute():
            raise ValueError("The output folder must be an absolute path.")
        target.mkdir(parents=True, exist_ok=True)
        speed = max(SPEED_MIN, min(SPEED_MAX, float(payload.get("speed") or 1.0)))
        preserve_groups = bool(payload.get("preserve_groups"))
        item_map = library.item_map()
        used_names: set[str] = set()
        exported: list[str] = []
        for item_id in item_ids:
            item = item_map[item_id]
            destination = copy_item_to(
                library,
                item,
                target,
                speed=speed,
                preserve_groups=preserve_groups,
                used_names=used_names,
            )
            exported.append(str(destination))
        with state.lock:
            state.allowed_export_dirs.add(str(target.resolve()))
        return jsonify({"count": len(exported), "target_dir": str(target.resolve()), "files": exported})

    @app.post("/api/reveal")
    def reveal():
        payload = request.get_json(silent=True) or {}
        target = str(payload.get("target_dir") or "")
        try:
            resolved = str(Path(target).resolve())
        except OSError:
            return _json_error("Invalid folder.", 400)
        with state.lock:
            allowed = resolved in state.allowed_export_dirs
        if not allowed:
            return _json_error("Folder was not created by this session.", 403)
        if sys.platform != "win32":
            return _json_error("Opening folders is only supported on Windows.", 400)
        os.startfile(resolved)  # type: ignore[attr-defined]
        return jsonify({"ok": True})

    @app.delete("/api/libraries/<library_id>")
    def delete_library(library_id: str):
        with state.lock:
            library = state.libraries.pop(library_id, None)
        if library is None:
            return _json_error("Library not found.", 404)
        shutil.rmtree(library.root, ignore_errors=True)
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8765, debug=False, threaded=True)
