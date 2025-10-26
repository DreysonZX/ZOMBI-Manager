from __future__ import annotations
import os
import sys
import traceback
import tempfile

from typing import Optional, Dict

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QPushButton, QMessageBox,
    QMenuBar, QStatusBar, QProgressDialog, QLabel, QTextEdit, QSplitter, QMenu,
)
from PySide6.QtGui import QAction, QPixmap, QImage, QPalette, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# ----------------- Utilities -----------------
from utilities import bfz
from utilities import previewers
from utilities import textureFile
# ----------------- Main UI -----------------

class PreviewPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        self.title = QLabel("No file selected")
        self.title.setWordWrap(True)
        self.image_label = QLabel()
        self.image_label.setFixedSize(400, 400)
        self.image_label.setScaledContents(True)
        self.meta = QTextEdit()
        self.meta.setReadOnly(True)
        self.meta.setFixedHeight(140)

        self.play_btn, self.pause_btn = QPushButton("Play"), QPushButton("Pause")
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.play_btn.clicked.connect(lambda: self.player.play())
        self.pause_btn.clicked.connect(lambda: self.player.pause())
        h = QHBoxLayout(); h.addWidget(self.play_btn); h.addWidget(self.pause_btn); h.addStretch(1)

        v.addWidget(self.title)
        v.addWidget(self.image_label, 1)
        v.addLayout(h)
        v.addWidget(self.meta)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.current_temp_audio = None

    def clear(self):
        self.title.setText("No file selected")
        self.image_label.clear()
        self.meta.clear()
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        if self.current_temp_audio:
            try: os.unlink(self.current_temp_audio)
            except Exception: pass
            self.current_temp_audio = None
        self.player.stop()

    def preview_bytes(self, name: str, data: bytes):
        self.clear()
        self.title.setText(name)
        lower = name.lower()
        if lower.endswith(".son"):
            wav = previewers.extract_wav_from_son(data)
            if wav:
                meta = previewers.get_wav_metadata(wav)
                txt = (f"WAV embedded: {meta['channels']} ch, {meta['sample_rate']} Hz, "
                       f"{meta['sampwidth']*8} bit, {meta['duration']:.2f}s\n"
                       f"Size: {len(wav)} bytes") if meta else f"Embedded WAV ({len(wav)} bytes)"
                self.meta.setPlainText(txt)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                tmp.write(wav); tmp.close()
                self.current_temp_audio = tmp.name
                self.player.setSource(QUrl.fromLocalFile(tmp.name))
                self.play_btn.setEnabled(True); self.pause_btn.setEnabled(True)
                return
            self.meta.setPlainText("No RIFF/WAVE found inside .son\n\n" + bytes_preview(data))
            return
        elif lower.endswith(".tdt"):
            try:
                img = textureFile.decode_tdt(data)
                if img:
                    pix = QPixmap.fromImage(QImage(img))
                    self.image_label.setPixmap(pix)
                    self.meta.setPlainText(f"TDT decoded: {img.width}x{img.height}")
                else:
                    self.meta.setPlainText("Unsupported or failed TDT decode.\n\n" + bytes_preview(data))
            except Exception as e:
                self.meta.setPlainText(f"Failed to parse TDT:\n{e}\n\n" + bytes_preview(data))
            return

        self.meta.setPlainText(f"Generic file ({len(data)} bytes)\n\n" + bytes_preview(data))

def bytes_preview(data: bytes, n: int = 256) -> str:
    s = data[:n]
    hexs = ' '.join(f"{b:02x}" for b in s)
    ascii_rep = ''.join((chr(b) if 32 <= b < 127 else '.') for b in s)
    return f"Hex (first {min(len(data), n)} bytes):\n{hexs}\n\nASCII:\n{ascii_rep}"

# ----------------- Main Window -----------------

class ZombiManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZOMBI Manager")
        self.setMinimumSize(QSize(1000, 700))
        self._apply_gray_theme()
        self.archive: Optional[bfz.BFZArchive] = None
        self.current_archive_path: Optional[str] = None

        central = QWidget(self); self.setCentralWidget(central)
        main_layout = QVBoxLayout(central); splitter = QSplitter(Qt.Horizontal)

        #self.tree = QTreeWidget(); self.tree.setHeaderHidden(True)
        #self.tree.setColumnCount(1)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Name", "Size", "Type"])
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_context_menu)

        left_widget = QWidget(); left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(self.tree)
        self.export_all_btn = QPushButton("Export All"); self.export_all_btn.setEnabled(False)
        self.export_all_btn.clicked.connect(self.export_all)
        left_layout.addWidget(self.export_all_btn)

        self.preview = PreviewPane()
        splitter.addWidget(left_widget); splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 3); splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter)

        self.setMenuBar(self._make_menu()); self.setStatusBar(QStatusBar())

    def _apply_gray_theme(self):
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(56, 56, 56))
        pal.setColor(QPalette.Base, QColor(46, 46, 46))
        pal.setColor(QPalette.AlternateBase, QColor(60, 60, 60))
        pal.setColor(QPalette.Button, QColor(70, 70, 70))
        pal.setColor(QPalette.Text, QColor(230, 230, 230))
        pal.setColor(QPalette.ButtonText, QColor(230, 230, 230))
        pal.setColor(QPalette.WindowText, QColor(240, 240, 240))
        self.setPalette(pal)

    def _make_menu(self):
        menubar = QMenuBar()
        file_menu = menubar.addMenu("File")

        act_open = QAction("Load File", self)
        act_open.triggered.connect(self.on_open)
        file_menu.addAction(act_open)

        act_import = QAction("Import Folder → BFZ", self)
        act_import.triggered.connect(self.on_import_folder)
        file_menu.addAction(act_import)

        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        return menubar
        
    def on_import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder to import")
        if not folder:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save BFZ as...", "", "BFZ Archive (*.bfz);;All Files (*)")
        if not out_path:
            return
        try:
            progress = QProgressDialog("Building BFZ…", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.processEvents()
            #build_bfz_from_folder(folder, out_path)
            progress.close()
            QMessageBox.information(self, "Done", f"Built BFZ:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Import error", f"Failed to build BFZ:\n{e}\n\n{traceback.format_exc()}")
    
    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open BFZ Archive", "", "BFZ Archives (*.bfz);;All Files (*)")
        if not path: return
        try:
            self.statusBar().showMessage("Parsing archive…")
            progress = QProgressDialog("Parsing…", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal); progress.setAutoClose(True); progress.show()
            QApplication.processEvents()
            arch = bfz.BFZArchive(path); arch.parse(progress=progress)
            self.archive, self.current_archive_path = arch, path
            self.populate_tree(); self.export_all_btn.setEnabled(True)
            self.statusBar().showMessage(f"Loaded: {os.path.basename(path)} ({len(arch.file_entries)} files)")
            self.setWindowTitle(f"ZOMBI Manager: {os.path.basename(path)} ({len(arch.file_entries)} files)")
        except Exception as e:
            self.statusBar().clearMessage(); self.export_all_btn.setEnabled(False); self.tree.clear()
            QMessageBox.critical(self, "Error", f"Failed to load archive:\n\n{e}\n\n{traceback.format_exc()}")
            self.setWindowTitle("ZOMBI Manager")

    def populate_tree(self):
        self.tree.clear()
        if not self.archive:
            return

        root_map: Dict[str, QTreeWidgetItem] = {}
        grouped: Dict[str, list] = {}

        # Normalize the path
        for entry in self.archive.file_entries:
            path = entry.name.replace("\\", "/").strip("/")
            grouped.setdefault(path, []).append(entry)

        for path, entries in grouped.items():
            parts = [p for p in path.split("/") if p]
            if not parts:
                continue

            parent_item, cur_map = None, root_map
            for i, part in enumerate(parts):
                is_leaf = (i == len(parts) - 1)
                key = (id(parent_item), part)
                if key not in cur_map:
                    if is_leaf:
                        # This will be the base entry, if theres multiple, it will be the parent
                        size_str = f"{entries[0].size:,}"
                        ext = os.path.splitext(entries[0].name)[1].lower() or "-"
                        cols = [part, size_str, ext]
                    else:
                        cols = [part, "", ""]
                    item = QTreeWidgetItem(cols)
                    (self.tree.addTopLevelItem if parent_item is None else parent_item.addChild)(item)
                    cur_map[key] = item

                item = cur_map[key]
                parent_item = item

                # Make sub items for duplicates
                if is_leaf:
                    if len(entries) == 1:
                        item.setData(0, Qt.UserRole, entries[0])
                    else:
                        for idx, dup_entry in enumerate(entries):
                            sub = QTreeWidgetItem([
                                f"[Variant #{idx+1}]",
                                f"{dup_entry.size:,}",
                                os.path.splitext(dup_entry.name)[1].lower() or "-"
                            ])
                            sub.setData(0, Qt.UserRole, dup_entry)
                            item.addChild(sub)

        # Size it
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
        self.tree.sortItems(0, Qt.AscendingOrder)
        self.tree.expandToDepth(2)
        
    def on_item_clicked(self, item: QTreeWidgetItem, col: int):
        entry = item.data(0, Qt.UserRole)
        if not entry or not self.archive: self.preview.clear(); return
        try:
            data = self.archive.read_file_bytes(entry)
            self.preview.preview_bytes(entry.name, data)
        except Exception as e:
            QMessageBox.critical(self, "Preview error", f"Failed to read file bytes:\n{e}")

    def on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        entry = item.data(0, Qt.UserRole)
        if not entry: return
        menu = QMenu()
        act_export = QAction("Export File...", self)
        act_export.triggered.connect(lambda: self.export_single(entry))
        act_export_raw = QAction("Export Raw File...", self)
        act_export_raw.triggered.connect(lambda: self.export_single(entry, raw=True))
        menu.addAction(act_export); menu.addAction(act_export_raw)
        if entry.name.lower().endswith(".tdt"):
            act_export_png = QAction("Export as PNG...", self)
            act_export_png.triggered.connect(lambda: textureFile.export_tdt_as_png(entry))
            menu.addAction(act_export_png)
        menu.exec(self.tree.mapToGlobal(pos))

    def export_single(self, entry: bfz.BFZFileEntry, raw: bool = False):
        if not self.archive: return
        default_name = os.path.basename(entry.name) or "file.bin"
        path, _ = QFileDialog.getSaveFileName(self, "Export file", default_name)
        if not path: return
        try:
            data = self.archive.read_file_bytes(entry)
            if (not raw) and entry.name.lower().endswith(".son"):
                wav = previewers.extract_wav_from_son(data)
                if wav:
                    out_path = path if path.lower().endswith(".wav") else path + ".wav"
                    with open(out_path, "wb") as w: w.write(wav)
                    QMessageBox.information(self, "Exported", f"Exported embedded WAV to:\n{out_path}")
                    return
            with open(path, "wb") as w: w.write(data)
            QMessageBox.information(self, "Exported", f"Exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export error", f"Failed to export:\n{e}\n\n{traceback.format_exc()}")

    def export_all(self):
        if not self.archive: return
        dir_ = QFileDialog.getExistingDirectory(self, "Select output directory")
        if not dir_: return
        try:
            progress = QProgressDialog("Exporting all…", "Cancel", 0, len(self.archive.file_entries), self)
            progress.setWindowModality(Qt.WindowModal); progress.show()
            QApplication.processEvents()
            for i, entry in enumerate(self.archive.file_entries):
                data = self.archive.read_file_bytes(entry)
                out_path = os.path.join(dir_, entry.name.replace("\\", "/"))
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as w: w.write(data)
                progress.setValue(i+1); QApplication.processEvents()
                if progress.wasCanceled(): break
            progress.close(); QMessageBox.information(self, "Done", f"Exported {len(self.archive.file_entries)} files")
        except Exception as e:
            QMessageBox.critical(self, "Export error", f"Failed to export all:\n{e}\n\n{traceback.format_exc()}")

# ----------------- Main -----------------

def main():
    app = QApplication(sys.argv)
    win = ZombiManager(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
