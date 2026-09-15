"""Launch WeChat Emoticon Studio as a native desktop window."""

from __future__ import annotations

import argparse
import multiprocessing
import socket
import subprocess
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from werkzeug.serving import make_server

from backend.app import create_app

EDGE_PATHS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)
CHROME_PATHS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)


class DesktopApi:
    """Native capabilities exposed to the WebView frontend."""

    def choose_save_path(self, suggested_name: str) -> str:
        import webview

        if not webview.windows:
            return ""
        result = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=suggested_name,
            file_types=("GIF 动图 (*.gif)", "所有文件 (*.*)"),
        )
        if isinstance(result, (tuple, list)):
            return str(result[0]) if result else ""
        return str(result or "")


def _available_port(preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port was found.")


def _open_app_window(url: str) -> None:
    browser = next((path for path in (*EDGE_PATHS, *CHROME_PATHS) if path.is_file()), None)
    if browser:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [str(browser), f"--app={url}", "--new-window"],
            creationflags=creation_flags,
        )
        return
    webbrowser.open(url)


def _wait_until_ready(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=0.5):
                return
        except Exception as error:
            last_error = error
            time.sleep(0.1)
    raise RuntimeError(f"The local application server did not start: {last_error}")


def _run_browser(app, host: str, port: int) -> int:
    port = _available_port(port)
    url = f"http://{host}:{port}"
    threading.Timer(0.7, lambda: _open_app_window(url)).start()
    print(f"WeChat Emoticon Studio: {url}", flush=True)
    app.run(
        host=host,
        port=port,
        debug=False,
        threaded=True,
        use_reloader=False,
    )
    return 0


def _run_desktop(app, host: str, debug: bool) -> int:
    try:
        import webview
    except ImportError as error:
        raise RuntimeError(
            "pywebview is required for the desktop window. "
            "Install app dependencies or run with --browser."
        ) from error

    server = make_server(host, 0, app, threaded=True)
    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
        name="studio-http-server",
    )
    server_thread.start()
    url = f"http://{host}:{server.server_port}"
    try:
        _wait_until_ready(url)
        webview.create_window(
            "微信表情工坊",
            url,
            width=1280,
            height=820,
            min_size=(900, 620),
            maximized=True,
            background_color="#f3f1ec",
            text_select=False,
            js_api=DesktopApi(),
        )
        webview.start(
            gui="edgechromium",
            debug=debug,
            private_mode=False,
        )
    finally:
        server.shutdown()
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WeChat Emoticon Studio.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--browser", action="store_true", help="Use the default browser instead of a desktop window.")
    parser.add_argument("--debug", action="store_true", help="Enable the WebView developer tools.")
    args = parser.parse_args()

    app = create_app()
    try:
        if args.browser:
            return _run_browser(app, args.host, args.port)
        return _run_desktop(app, args.host, args.debug)
    except RuntimeError as error:
        print(error, flush=True)
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
