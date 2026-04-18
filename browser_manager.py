import subprocess
import time
import requests
import os
import socket
from pathlib import Path
from playwright.sync_api import sync_playwright
from typing import Optional, Tuple

class BrowserManager:
    def __init__(self, account_id: str, user_data_dir: str, profile_dir: str = None,
                 debug_port: int = None, proxy: Optional[str] = None):
        self.account_id = account_id
        self.user_data_dir = user_data_dir
        self.profile_dir = profile_dir
        self.debug_port = debug_port or self._find_free_port()
        self.proxy = proxy
        self.chrome_process = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def _find_free_port(self) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def _launch_chrome(self):
        chrome_paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
        ]
        chrome_exe = None
        for p in chrome_paths:
            if os.path.exists(p):
                chrome_exe = p
                break
        if not chrome_exe:
            raise Exception("Chrome executable not found")

        args = [
            chrome_exe,
            f"--remote-debugging-port={self.debug_port}",
            f"--user-data-dir={self.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
            "--disable-default-apps",
            "--disable-sync",
        ]
        if self.profile_dir:
            args.append(f"--profile-directory={self.profile_dir}")
        if self.proxy:
            args.append(f"--proxy-server={self.proxy}")

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # 0 = ẩn, 1 = hiện

        self.chrome_process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            shell=False
        )

        # Đợi Chrome mở cổng, tăng timeout lên 30 giây
        for attempt in range(30):
            time.sleep(1)
            try:
                resp = requests.get(f"http://localhost:{self.debug_port}/json/version", timeout=2)
                if resp.status_code == 200:
                    print(f"[OK] Chrome launched on port {self.debug_port}")
                    return
            except:
                continue
        raise Exception("Chrome did not open debug port in time")

    def _connect_playwright(self):
        self.playwright = sync_playwright().start()
        resp = requests.get(f"http://localhost:{self.debug_port}/json/version")
        ws_endpoint = resp.json()["webSocketDebuggerUrl"]
        self.browser = self.playwright.chromium.connect_over_cdp(ws_endpoint)
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def launch(self) -> Tuple:
        print(f"[START] Launching Chrome for {self.account_id}")
        self._launch_chrome()
        self._connect_playwright()
        if "gemini" not in self.page.url:
            self.page.goto("https://gemini.google.com", wait_until="domcontentloaded")
            time.sleep(3)
        return self.browser, self.context, self.page

    def close(self):
        print(f"[Closing] {self.account_id}")
        # Đóng page
        if hasattr(self, 'page') and self.page:
            try:
                if not self.page.is_closed():
                    self.page.close()
            except:
                pass
        # Đóng context
        if hasattr(self, 'context') and self.context:
            try:
                self.context.close()
            except:
                pass
        # Đóng browser
        if hasattr(self, 'browser') and self.browser:
            try:
                self.browser.close()
            except:
                pass
        # Dừng playwright
        if hasattr(self, 'playwright') and self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
        # Tắt Chrome process (nếu có)
        if hasattr(self, 'chrome_process') and self.chrome_process:
            try:
                self.chrome_process.terminate()
            except:
                pass
        print(f"[Closed] {self.account_id}")