"""
mini_chrome_full.py
Single-file PyQt6 mini-browser with:
- tabs, back/forward, reload, home
- bookmarks bar
- dark mode UI, simple theme toggle
- popup blocker and a simple adblocker
- persistent data stored in mini_chrome_data.json

Fix included for Windows GPU/PRN issues.

Requires:
    pip install PyQt6 PyQt6-WebEngine
"""

import os
import sys
import json
import re

# Fix GPU / PRN errors on Windows
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer"

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QMenu, QListWidget, QInputDialog,
    QMessageBox, QCompleter, QTabWidget
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QUrl, Qt, QSize

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineUrlRequestInterceptor

# ---------- persistent storage ----------
DATA_FILE = os.path.join(os.path.dirname(__file__), "mini_chrome_data.json")

def load_data():
    if os.path.isfile(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(d):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except Exception as e:
        print("Could not save data:", e)

state = load_data()
if "bookmarks" not in state: state["bookmarks"] = []
if "home" not in state: state["home"] = "https://www.google.com"
if "adblock" not in state: state["adblock"] = True
if "block_list" not in state:
    state["block_list"] = [
        "doubleclick.net", "googlesyndication", "adservice.google.com", "ads.",
        "amazon-adsystem.com", "pagead2.googlesyndication.com", "adserver", "adsystem"
    ]

# ---------- request interceptor ----------
class SimpleRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)

    def interceptRequest(self, info):
        try:
            if not state.get("adblock", True):
                return
            url = info.requestUrl().toString()
            for pat in state.get("block_list", []):
                if pat and pat.lower() in url.lower():
                    try:
                        info.block(True)
                    except Exception:
                        pass
                    return
        except Exception:
            return

# Register interceptor - must be called after QApplication is created
def register_interceptor():
    try:
        profile = QWebEngineProfile.defaultProfile()
        interceptor = SimpleRequestInterceptor()
        _registered = False
        try:
            if hasattr(profile, "setUrlRequestInterceptor"):
                profile.setUrlRequestInterceptor(interceptor)
                _registered = True
        except Exception:
            _registered = False
        if not _registered:
            try:
                if hasattr(profile, "setRequestInterceptor"):
                    profile.setRequestInterceptor(interceptor)
                    _registered = True
            except Exception:
                _registered = False
    except Exception:
        pass

# ---------- known sites ----------
KNOWN_SITES = {
    "google":"https://www.google.com", "youtube":"https://www.youtube.com", "yt":"https://www.youtube.com",
    "gmail":"https://mail.google.com", "tiktok":"https://www.tiktok.com","roblox":"https://www.roblox.com",
    "discord":"https://www.discord.com","reddit":"https://www.reddit.com","instagram":"https://www.instagram.com",
    "fortnite":"https://www.fortnite.com","fn":"https://www.fortnite.com",
    "xbox":"https://www.xbox.com/play","xplay":"https://www.xbox.com/play",
    "epic":"https://store.epicgames.com","epicgames":"https://store.epicgames.com"
}

def build_completer_list():
    items = list(KNOWN_SITES.keys())
    items += [bm.get("title") or bm.get("url") for bm in state.get("bookmarks", [])]
    seen = set()
    res = []
    for it in items:
        if not it: continue
        it = str(it)
        if it in seen: continue
        seen.add(it)
        res.append(it)
    return res

# ---------- WebView ----------
class WebView(QWebEngineView):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window

    def createWindow(self, _type):
        if not self.main_window or not getattr(self.main_window, "allow_popups", False):
            return None
        view = self.main_window.add_webview_tab(open_now=False)
        return view

# ---------- Main Window ----------
class MiniChrome(QMainWindow):
    def __init__(self):
        super().__init__()
        register_interceptor()  # ensure interceptor registered after QApplication exists
        self.setWindowTitle("Mini Chrome")
        self.resize(1200, 800)

        self.allow_popups = False
        self.dark_mode = False

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        # Toolbar
        navbar = QToolBar("Navigation")
        navbar.setIconSize(QSize(16,16))
        self.addToolBar(navbar)

        self.back_btn = QAction("◀", self)
        self.back_btn.triggered.connect(self.go_back)
        navbar.addAction(self.back_btn)

        self.forward_btn = QAction("▶", self)
        self.forward_btn.triggered.connect(self.go_forward)
        navbar.addAction(self.forward_btn)

        self.reload_btn = QAction("⤾", self)
        self.reload_btn.triggered.connect(self.reload_page)
        navbar.addAction(self.reload_btn)

        self.home_btn = QAction("🏠", self)
        self.home_btn.triggered.connect(self.go_home)
        navbar.addAction(self.home_btn)

        navbar.addSeparator()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Search or enter URL")
        self.url_input.returnPressed.connect(self.on_url_enter)
        navbar.addWidget(self.url_input)

        self.go_btn = QAction("Go", self)
        self.go_btn.triggered.connect(self.on_url_enter)
        navbar.addAction(self.go_btn)

        self.bookmark_btn = QAction("★", self)
        self.bookmark_btn.triggered.connect(self.add_bookmark)
        navbar.addAction(self.bookmark_btn)

        # Settings menu
        settings_menu = QMenu("Settings", self)
        self.dark_action = QAction("Dark mode", self, checkable=True)
        self.dark_action.triggered.connect(self.toggle_dark_mode)
        settings_menu.addAction(self.dark_action)

        self.popup_action = QAction("Allow popups", self, checkable=True)
        self.popup_action.triggered.connect(self.toggle_popups)
        settings_menu.addAction(self.popup_action)

        self.adblock_action = QAction("Adblock (simple)", self, checkable=True)
        self.adblock_action.setChecked(state.get("adblock", True))
        self.adblock_action.triggered.connect(self.toggle_adblock)
        settings_menu.addAction(self.adblock_action)

        cfg_action = QAction("Edit adblock patterns", self)
        cfg_action.triggered.connect(self.edit_block_list)
        settings_menu.addAction(cfg_action)

        menu_act = QAction("Settings", self)
        menu_act.setMenu(settings_menu)
        navbar.addAction(menu_act)

        # Bookmarks bar
        self.bookmark_bar = QToolBar("Bookmarks")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.bookmark_bar)
        self.bookmark_bar.setMovable(False)
        self.refresh_bookmark_bar()

        # Autocomplete
        completer = QCompleter(build_completer_list())
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.url_input.setCompleter(completer)

        # Status bar
        self.status = self.statusBar()
        self.status.showMessage("Ready")

        # New tab button
        new_tab_act = QAction("+", self)
        new_tab_act.triggered.connect(lambda: self.add_webview_tab("about:blank", True))
        navbar.addAction(new_tab_act)

        # Open home tab
        self.add_webview_tab(state.get("home", "https://www.google.com"), True)

    # ---------- UI ----------
    def refresh_bookmark_bar(self):
        self.bookmark_bar.clear()
        for bm in state.get("bookmarks", []):
            title = bm.get("title") or bm.get("url")
            url = bm.get("url")
            act = QAction(title, self)
            act.triggered.connect(lambda checked=False, u=url: self.open_url_in_current_tab(u))
            self.bookmark_bar.addAction(act)
        manage = QAction("Manage", self)
        manage.triggered.connect(self.manage_bookmarks)
        self.bookmark_bar.addAction(manage)

    def update_completer(self):
        comp = QCompleter(build_completer_list())
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.url_input.setCompleter(comp)

    # ---------- Tabs ----------
    def add_webview_tab(self, url=None, make_active=True, open_now=True):
        view = WebView(main_window=self)
        view.urlChanged.connect(lambda qurl, v=view: self.on_url_changed(v, qurl))
        view.titleChanged.connect(lambda title, v=view: self.on_title_changed(v, title))

        index = self.tabs.addTab(view, "New Tab")
        if url:
            if isinstance(url, str) and url.startswith("http"):
                view.load(QUrl(url))
            else:
                self._navigate_guess(view, url)
        if make_active:
            self.tabs.setCurrentIndex(index)
        return view

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(index)

    def current_webview(self):
        w = self.tabs.currentWidget()
        if isinstance(w, QWebEngineView):
            return w
        return None

    # ---------- Navigation ----------
    def go_back(self):
        v = self.current_webview()
        if v and v.history().canGoBack():
            v.back()

    def go_forward(self):
        v = self.current_webview()
        if v and v.history().canGoForward():
            v.forward()

    def reload_page(self):
        v = self.current_webview()
        if v:
            v.reload()

    def go_home(self):
        self.add_webview_tab(state.get("home", "https://www.google.com"), True)

    def open_url_in_current_tab(self, url):
        v = self.current_webview() or self.add_webview_tab()
        if not url.startswith("http"):
            url = "https://" + url
        v.load(QUrl(url))

    # ---------- URL guessing ----------
    def _guess_url_from_text(self, text):
        t = text.strip()
        if not t:
            return None
        low = t.lower()
        if low in KNOWN_SITES:
            return KNOWN_SITES[low]
        if "." in t and " " not in t:
            if not t.startswith("http"):
                return "https://" + t
            return t
        if re.match(r"^[a-zA-Z0-9\-]+$", t):
            return f"https://{t}.com"
        q = t.replace(" ", "+")
        return f"https://www.google.com/search?q={q}"

    def _navigate_guess(self, view, text):
        url = self._guess_url_from_text(text)
        if url:
            view.load(QUrl(url))

    def on_url_enter(self):
        text = self.url_input.text().strip()
        if not text:
            return
        view = self.current_webview() or self.add_webview_tab()
        url = self._guess_url_from_text(text)
        if url:
            view.load(QUrl(url))

    def on_url_changed(self, webview, qurl):
        if webview == self.current_webview():
            self.url_input.setText(qurl.toString())

    def on_title_changed(self, webview, title):
        idx = self.tabs.indexOf(webview)
        if idx >= 0:
            self.tabs.setTabText(idx, title or "New Tab")

    # ---------- Bookmarks ----------
    def add_bookmark(self):
        v = self.current_webview()
        if not v:
            return
        url = v.url().toString()
        title = v.title() or url
        for bm in state.get("bookmarks", []):
            if bm.get("url") == url:
                QMessageBox.information(self, "Bookmark", "Already bookmarked.")
                return
        state["bookmarks"].append({"title": title, "url": url})
        save_data(state)
        self.refresh_bookmark_bar()
        self.update_completer()
        QMessageBox.information(self, "Bookmark", f"Bookmarked: {title}")

    def manage_bookmarks(self):
        dlg = QListWidget()
        dlg.setWindowTitle("Manage bookmarks - select to remove (close when done)")
        for bm in state.get("bookmarks", []):
            dlg.addItem(f"{bm.get('title')}  —  {bm.get('url')}")
        dlg.setMinimumSize(600,400)
        dlg.show()
        def on_double(idx):
            row = idx.row()
            if row >= 0 and row < len(state.get("bookmarks", [])):
                del state["bookmarks"][row]
                save_data(state)
                self.refresh_bookmark_bar()
                dlg.takeItem(row)
        dlg.itemDoubleClicked.connect(lambda item: on_double(dlg.row(item)))

    # ---------- Settings ----------
    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background: #111; color: #ddd; }
                QToolBar { background: #222; color: #ddd; }
                QLineEdit { background: #222; color: #ddd; border: 1px solid #444; }
                QPushButton { background: #333; color: #ddd; }
            """)
        else:
            self.setStyleSheet("")
        self.dark_action.setChecked(self.dark_mode)

    def toggle_popups(self):
        self.allow_popups = not self.allow_popups
        self.popup_action.setChecked(self.allow_popups)

    def toggle_adblock(self):
        state["adblock"] = not state.get("adblock", True)
        save_data(state)
        self.adblock_action.setChecked(state["adblock"])
        QMessageBox.information(self, "Adblock", f"Adblock set to {state['adblock']}")

    def edit_block_list(self):
        text, ok = QInputDialog.getMultiLineText(self, "Edit adblock patterns",
            "Each pattern is matched as substring against requests' URL (one per line):",
            "\n".join(state.get("block_list", [])))
        if ok:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            state["block_list"] = lines
            save_data(state)
            QMessageBox.information(self, "Adblock", "Block list updated.")

# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MiniChrome()
    window.show()
    sys.exit(app.exec())
