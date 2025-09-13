from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Literal
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFileSystemWatcher
import pathlib

SourceType = Literal["file", "resource", "inline"]

@dataclass(order=True)
class StyleEntry:
    priority: int
    plugin_id: str
    key: str                 # unique key per plugin (e.g. "spectrogram", "sidebar_settings")
    source_type: SourceType  # file/resource/inline
    content: str             # QSS (inline) or path string
    enabled: bool = True

class Style:
    """
    Collects QSS from core + plugins and applies a merged sheet to the QApplication.
    """
    def __init__(self, app: QApplication, project_root: Optional[pathlib.Path] = None, dev_watch: bool = False):
        self._app = app
        self._entries: List[StyleEntry] = []
        self._watcher = QFileSystemWatcher() if dev_watch else None
        self._project_root = project_root or pathlib.Path.cwd()

        print(f"Style initialized with project root: {self._project_root}")
        if self._watcher:
            self._watcher.fileChanged.connect(self._on_file_changed)

    # --- public API for core/plugins ---
    def add_inline(self, plugin_id: str, key: str, qss: str, priority: int = 100):
        self._upsert(StyleEntry(priority, plugin_id, key, "inline", qss))
        self.apply()

    def add_file(self, plugin_id: str, key: str, path: str | pathlib.Path, priority: int = 100):
        self._upsert(StyleEntry(priority, plugin_id, key, "file", str(path)))
        if self._watcher and pathlib.Path(path).exists():
            self._watch_add(path)
        self.apply()

    def add_resource(self, plugin_id: str, key: str, resource_path: str, priority: int = 100):
        # e.g. ":/plugins/foo/style.qss"
        self._upsert(StyleEntry(priority, plugin_id, key, "resource", resource_path))
        self.apply()

    def remove(self, plugin_id: str, key: Optional[str] = None):
        before = len(self._entries)
        self._entries = [e for e in self._entries if not (e.plugin_id == plugin_id and (key is None or e.key == key))]
        if self._watcher:
            self._sync_watcher()
        if len(self._entries) != before:
            self.apply()

    def enable(self, plugin_id: str, key: str, enabled: bool = True):
        for e in self._entries:
            if e.plugin_id == plugin_id and e.key == key:
                e.enabled = enabled
        self.apply()

    def clear_all(self):
        self._entries.clear()
        if self._watcher:
            self._watcher.removePaths(self._watcher.files())
        self.apply()

    # --- internals ---
    def _upsert(self, entry: StyleEntry):
        for i, e in enumerate(self._entries):
            if e.plugin_id == entry.plugin_id and e.key == entry.key:
                self._entries[i] = entry
                return
        self._entries.append(entry)

    def _read_entry(self, e: StyleEntry) -> str:
        if not e.enabled:
            return ""
        if e.source_type == "inline":
            return e.content
        if e.source_type == "file":
            p = pathlib.Path(e.content)
            if not p.is_absolute():
                p = (self._project_root / e.content).resolve()
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                return f"/* failed to read {p} */"
        if e.source_type == "resource":
            # Qt resource file read via QFile (works for :/ paths)
            from PySide6.QtCore import QFile, QTextStream
            f = QFile(e.content)
            if not f.open(QFile.ReadOnly | QFile.Text):
                return f"/* failed to read resource {e.content} */"
            ts = QTextStream(f)
            ts.setCodec("UTF-8")
            return ts.readAll()
        return ""

    def apply(self):
        merged = []
        for e in sorted(self._entries):  # uses dataclass(order=True) -> priority then fields
            css = self._read_entry(e).strip()
            if css:
                merged.append(f"/* [{e.priority}] {e.plugin_id}:{e.key} */\n{css}\n")
        self._app.setStyleSheet("\n".join(merged))

    # ---- dev hot reload helpers ----
    def _watch_add(self, path: str):
        files = set(self._watcher.files()) if self._watcher else set()
        if self._watcher and path not in files:
            self._watcher.addPath(path)

    def _sync_watcher(self):
        if not self._watcher:
            return
        paths_needed = {e.content for e in self._entries if e.source_type == "file"}
        current = set(self._watcher.files())
        to_add = paths_needed - current
        to_remove = current - paths_needed
        if to_add:
            self._watcher.addPaths(list(to_add))
        if to_remove:
            self._watcher.removePaths(list(to_remove))

    def _on_file_changed(self, _path: str):
        # Some editors swap files -> re-add path to watch
        print(f"🖌️ Style changed: {_path}")
        if self._watcher:
            self._watcher.removePath(_path)
            try:
                self._watcher.addPath(_path)
            except Exception:
                pass
        self.apply()