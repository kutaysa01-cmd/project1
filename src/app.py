"""T3000 Problem Finder - PyQt6 desktop application.

Run with:
    python -m src.app
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import yaml
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.llm import LLMClient
from src.rag import Retriever


# ============================================================
# Theming
# ============================================================
DARK_QSS = """
    QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; }
    QLabel { color: #cdd6f4; }
    QLabel#title { font-size: 20px; font-weight: bold; color: #89b4fa; }
    QLabel#subtitle { color: #9399b2; font-size: 12px; }
    QLabel#section { font-size: 13px; font-weight: bold; color: #f9e2af; padding-top: 8px; }
    QPlainTextEdit, QTextEdit {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 10px;
        font-size: 13px;
    }
    QPushButton {
        background-color: #89b4fa;
        color: #1e1e2e;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
    }
    QPushButton:hover { background-color: #74c7ec; }
    QPushButton:pressed { background-color: #89dceb; }
    QPushButton:disabled { background-color: #45475a; color: #6c7086; }
    QPushButton#secondary {
        background-color: #45475a; color: #cdd6f4;
    }
    QPushButton#secondary:hover { background-color: #585b70; }
    QStatusBar { background-color: #181825; color: #a6adc8; border-top: 1px solid #313244; }
    QFrame#sources {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 6px;
        padding: 8px;
    }
    QSplitter::handle { background-color: #313244; }
"""


# ============================================================
# Background worker so UI never freezes while LLM is thinking
# ============================================================
class QueryWorker(QThread):
    chunk_received = pyqtSignal(str)
    sources_ready = pyqtSignal(list)
    finished_ok = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, retriever: Retriever, llm: LLMClient, question: str, lang: str):
        super().__init__()
        self.retriever = retriever
        self.llm = llm
        self.question = question
        self.lang = lang

    def run(self):
        try:
            chunks = self.retriever.retrieve(self.question)
            self.sources_ready.emit(chunks)
            if not chunks:
                msg = ("Bilgi tabanında ilgili kayıt bulunamadı. "
                       "Soruyu farklı ifade etmeyi dene veya daha fazla ticket ekle."
                       if self.lang == "tr" else
                       "No relevant records found. Rephrase or add more tickets.")
                self.chunk_received.emit(msg)
                self.finished_ok.emit()
                return
            for piece in self.llm.ask_stream(self.question, chunks, lang=self.lang):
                self.chunk_received.emit(piece)
            self.finished_ok.emit()
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


# ============================================================
# Main window
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.lang = config["ui"]["language"]
        self.worker: QueryWorker | None = None

        self.setWindowTitle("T3000 Problem Finder")
        self.resize(1200, 800)

        self._build_ui()
        self._init_backend()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Header
        header = QVBoxLayout()
        title = QLabel("T3000 Problem Finder")
        title.setObjectName("title")
        subtitle = QLabel("Offline AI assistant • Geçmiş ticket'lardan ve manuellerden cevap üretir")
        subtitle.setObjectName("subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        # Question input
        q_label = QLabel("SORU / QUESTION")
        q_label.setObjectName("section")
        root.addWidget(q_label)

        self.question_input = QPlainTextEdit()
        self.question_input.setPlaceholderText(
            "Problemi tarif et...\n"
            "Örn: Zone 3 sıcaklık sensörü -40°C okuyor, setpoint takip edilemiyor."
        )
        self.question_input.setMaximumHeight(100)
        root.addWidget(self.question_input)

        # Buttons
        btn_row = QHBoxLayout()
        self.ask_btn = QPushButton("Sor  (Ctrl+Enter)")
        self.ask_btn.clicked.connect(self._on_ask)
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.ask_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Answer + sources (split)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Answer pane
        ans_container = QWidget()
        ans_layout = QVBoxLayout(ans_container)
        ans_layout.setContentsMargins(0, 0, 0, 0)
        ans_label = QLabel("CEVAP / ANSWER")
        ans_label.setObjectName("section")
        ans_layout.addWidget(ans_label)
        self.answer_view = QTextEdit()
        self.answer_view.setReadOnly(True)
        self.answer_view.setFont(QFont("Segoe UI", 11))
        ans_layout.addWidget(self.answer_view)
        splitter.addWidget(ans_container)

        # Sources pane
        src_container = QWidget()
        src_layout = QVBoxLayout(src_container)
        src_layout.setContentsMargins(0, 0, 0, 0)
        src_label = QLabel("KAYNAKLAR / SOURCES")
        src_label.setObjectName("section")
        src_layout.addWidget(src_label)
        self.sources_view = QTextEdit()
        self.sources_view.setReadOnly(True)
        self.sources_view.setFrameShape(QFrame.Shape.NoFrame)
        src_layout.addWidget(self.sources_view)
        splitter.addWidget(src_container)

        splitter.setSizes([500, 200])
        root.addWidget(splitter, 1)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Shortcut
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_ask)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_ask)

        # Theme
        if self.config["ui"]["theme"] == "dark":
            self.setStyleSheet(DARK_QSS)

    # ---------- Backend init ----------
    def _init_backend(self):
        self.status.showMessage("Başlatılıyor...")
        try:
            self.retriever = Retriever(self.config)
            n = self.retriever.count()
        except FileNotFoundError as e:
            QMessageBox.warning(self, "Vector DB yok", str(e))
            self.retriever = None
            n = 0
        except Exception as e:
            QMessageBox.critical(self, "Retriever hatası", f"{e}")
            self.retriever = None
            n = 0

        self.llm = LLMClient(
            model=self.config["llm"]["model"],
            host=self.config["llm"]["host"],
            temperature=self.config["llm"]["temperature"],
            num_ctx=self.config["llm"]["num_ctx"],
        )
        ok, msg = self.llm.check_connection()
        parts = [f"{n} chunk indexed" if self.retriever else "DB yok"]
        parts.append(f"LLM: {self.config['llm']['model']} - {msg}")
        self.status.showMessage(" | ".join(parts))
        if not ok:
            QMessageBox.warning(self, "Ollama uyarısı", msg)

    # ---------- Actions ----------
    def _on_ask(self):
        if self.worker and self.worker.isRunning():
            return
        question = self.question_input.toPlainText().strip()
        if not question:
            return
        if not self.retriever:
            QMessageBox.warning(
                self, "Veritabanı yok",
                "Önce 'python -m src.ingest' çalıştırarak veritabanını oluştur."
            )
            return

        self.answer_view.clear()
        self.sources_view.clear()
        self.ask_btn.setEnabled(False)
        self.ask_btn.setText("Düşünüyor...")

        self.worker = QueryWorker(self.retriever, self.llm, question, self.lang)
        self.worker.chunk_received.connect(self._append_answer_chunk)
        self.worker.sources_ready.connect(self._show_sources)
        self.worker.finished_ok.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _append_answer_chunk(self, text: str):
        cursor = self.answer_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.answer_view.setTextCursor(cursor)
        self.answer_view.ensureCursorVisible()

    def _show_sources(self, chunks: list[dict]):
        if not chunks:
            self.sources_view.setPlainText("(hiç kaynak bulunamadı)")
            return
        lines = []
        for i, c in enumerate(chunks, 1):
            meta = c.get("metadata", {})
            score = c.get("score", 0.0)
            src = meta.get("ticket_id") or meta.get("title") or Path(meta.get("source", "?")).name
            kind = meta.get("type", "?")
            preview = c["document"][:200].replace("\n", " ")
            lines.append(f"[{i}] {kind.upper()} • {src} • benzerlik: {score:.2f}")
            lines.append(f"    {preview}...")
            lines.append("")
        self.sources_view.setPlainText("\n".join(lines))

    def _on_done(self):
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Sor  (Ctrl+Enter)")

    def _on_error(self, msg: str):
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Sor  (Ctrl+Enter)")
        QMessageBox.critical(self, "Hata", msg)

    def _on_clear(self):
        self.question_input.clear()
        self.answer_view.clear()
        self.sources_view.clear()


# ============================================================
# Entry point
# ============================================================
def main():
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("ERROR: config.yaml bulunamadı. Proje klasöründe çalıştır.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    app = QApplication(sys.argv)
    app.setApplicationName("T3000 Problem Finder")
    win = MainWindow(config)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
