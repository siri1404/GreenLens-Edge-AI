# green_len_2_integrated.py
import sys, json, os, requests
from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSpacerItem, QSizePolicy, QStackedWidget,
    QTextEdit, QLineEdit, QMessageBox, QFileDialog
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QIcon, QPixmap, QImage, QTextCursor
)
from PyQt6.QtCore import Qt, QSize, QRectF, QTimer, QThread, pyqtSignal
import cv2

# =========================
# Backend selection
# =========================
BACKEND = os.environ.get("GL_BACKEND", "").lower()  # "npu" or "ollama"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama2:7b-chat")

# Try import the repo’s NPU engine if it exists (simple adapter)
class NPUAdapter:
    def __init__(self):
        self.ok = False
        try:
            # these names are generic; change if the repo exposes different entrypoints
            # we try a few common options:
            try:
                from engine import Engine  # hypothetical
                self.engine = Engine()
                self.ok = True
            except Exception:
                self.engine = None
        except Exception:
            self.engine = None

    def available(self) -> bool:
        return self.ok

    def generate(self, prompt: str) -> str:
        """Return a single string response from the NPU engine."""
        # If your repo has a different API, adapt here:
        # e.g. self.engine.chat(prompt) or self.engine.generate([prompt])
        if not self.ok:
            raise RuntimeError("NPU backend not available")
        return self.engine.generate(prompt)  # <- adjust to your repo

NPU = NPUAdapter()
USE_NPU = (BACKEND == "npu" and NPU.available())

# =========================
# Color palette
# =========================
COLOR_BACKGROUND = "#121212"
COLOR_NAV_MENU = "#1E1E1E"
COLOR_CONTENT_AREA = "#1A1A1A"
COLOR_CARD_BACKGROUND = "#2A2A2A"
COLOR_CARD_BORDER = "#444444"
COLOR_PRIMARY_GREEN = "#4CAF50"
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#AAAAAA"
COLOR_ACCENT_AI = "#66FF66"
COLOR_ACTIVE_NAV_BAR = "#39FF14"

# =========================
# Worker threads
# =========================
class OllamaWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, url: str, model: str, prompt: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            payload = {"model": self.model, "prompt": self.prompt, "stream": False}
            r = requests.post(self.url, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            reply = (data.get("response") or "").strip()
            if not reply:
                reply = "(No response)"
            self.response_ready.emit(reply)
        except Exception as e:
            self.response_ready.emit(f"(Error contacting Ollama: {e})")

class NPUWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, prompt: str, parent=None):
        super().__init__(parent)
        self.prompt = prompt

    def run(self):
        try:
            reply = NPU.generate(self.prompt)
            if not reply:
                reply = "(No response)"
            self.response_ready.emit(reply)
        except Exception as e:
            self.response_ready.emit(f"(NPU error: {e})")

# =========================
# Custom widgets
# =========================
class CircularProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 85
        self.setFixedSize(180, 180)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(10, 10, self.width() - 20, self.height() - 20)

        pen = QPen(QColor(COLOR_CARD_BORDER), 14)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect.toRect(), 90 * 16, 360 * 16)

        pen.setColor(QColor(COLOR_PRIMARY_GREEN))
        p.setPen(pen)
        angle = int(self.value / 100.0 * 360)
        p.drawArc(rect.toRect(), 90 * 16, -angle * 16)

        p.setPen(QColor(COLOR_TEXT_PRIMARY))
        font = QFont("Segoe UI", 36, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}%")

        p.setPen(QColor(COLOR_TEXT_SECONDARY))
        font.setPointSize(14)
        font.setWeight(QFont.Weight.Normal)
        p.setFont(font)
        text_rect = QRectF(rect.x(), rect.y() + rect.height() * 0.65, rect.width(), rect.height() * 0.35)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Green Choices")

class NavButton(QPushButton):
    def __init__(self, text, icon_path, is_active=False, parent=None):
        super().__init__(text, parent)
        self.setObjectName("NavButton")
        try:
            self.setIcon(QIcon(icon_path))
        except Exception:
            self.setText(text)
            self.setIcon(QIcon())
        self.setIconSize(QSize(20, 20))
        self.setProperty("active", is_active)
        self.setCheckable(True)
        self.setChecked(is_active)
        self.setMinimumHeight(45)

# =========================
# Pages
# =========================
class ScanPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ScanPage")
        self.camera = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setSpacing(20)

        title = QLabel("Scan Product")
        title.setObjectName("PageTitleLabel")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)

        container = QFrame()
        container.setObjectName("CameraViewContainer")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)

        self.camera_feed_label = QLabel("Camera Feed will appear here...")
        self.camera_feed_label.setObjectName("CameraFeedLabel")
        self.camera_feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_feed_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        v.addWidget(self.camera_feed_label)
        layout.addWidget(container)

        bar = QHBoxLayout()
        self.capture_btn = QPushButton("Capture Image")
        self.capture_btn.setObjectName("AnalyzeButton")
        self.capture_btn.setMinimumHeight(50)
        self.capture_btn.clicked.connect(self.capture_frame)

        bar.addStretch()
        bar.addWidget(self.capture_btn)
        bar.addStretch()
        layout.addLayout(bar)

    def start_camera(self):
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                self.camera = None
                self.camera_feed_label.setText("Error: Could not open camera.")
                return
        self.timer.start(30)

    def update_frame(self):
        if self.camera is not None and self.camera.isOpened():
            ok, frame = self.camera.read()
            if ok:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img).scaled(
                    self.camera_feed_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.camera_feed_label.setPixmap(pixmap)
            else:
                self.camera_feed_label.setText("Error: Could not read frame from camera.")
        else:
            self.camera_feed_label.setText("Camera not active.")

    def capture_frame(self):
        if self.camera is None or not self.camera.isOpened():
            QMessageBox.warning(self, "Camera", "Camera is not active.")
            return
        ok, frame = self.camera.read()
        if not ok:
            QMessageBox.warning(self, "Camera", "Failed to capture frame.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save capture", "capture.jpg", "Images (*.jpg *.png)")
        if path:
            cv2.imwrite(path, frame)
            QMessageBox.information(self, "Saved", f"Frame saved to:\n{path}")

    def stop_camera(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            self.camera_feed_label.setText("Camera stopped.")

    def hideEvent(self, e):
        self.stop_camera()
        super().hideEvent(e)

    def showEvent(self, e):
        self.start_camera()
        super().showEvent(e)

class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPage")
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setSpacing(12)

        title = QLabel("AI Chat")
        title.setObjectName("PageTitleLabel")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setMinimumHeight(420)
        self.history.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0f0f0f;
                border: 1px solid {COLOR_PRIMARY_GREEN};
                border-radius: 10px;
                padding: 12px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 14px;
            }}
        """)
        layout.addWidget(self.history, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type your message…")
        self.input.returnPressed.connect(self.send_message)
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("AnalyzeButton")
        self.send_btn.clicked.connect(self.send_message)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        mode = "NPU (repo)" if USE_NPU else f"Ollama ({OLLAMA_MODEL})"
        note = QLabel(f"Backend: {mode}")
        note.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:12px;")
        layout.addWidget(note)

    def append_line(self, who: str, text: str):
        self.history.moveCursor(QTextCursor.MoveOperation.End)
        self.history.insertPlainText(f"{who}: {text}\n\n")
        self.history.moveCursor(QTextCursor.MoveOperation.End)

    def send_message(self):
        text = self.input.text().strip()
        if not text:
            return
        self.append_line("You", text)
        self.input.clear()

        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.append_line("Assistant", "…")

        if USE_NPU:
            self.worker = NPUWorker(text, self)
        else:
            self.worker = OllamaWorker(OLLAMA_URL, OLLAMA_MODEL, text, self)

        self.worker.response_ready.connect(self.handle_response)
        self.worker.finished.connect(self.finish_worker)
        self.worker.start()

    def handle_response(self, reply: str):
        # replace the last "…" with the real reply
        doc = self.history.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock, QTextCursor.MoveMode.KeepAnchor)
        last_text = cursor.selectedText()
        if last_text.strip() == "Assistant: …":
            cursor.removeSelectedText()
            self.history.moveCursor(QTextCursor.MoveOperation.End)
        self.append_line("Assistant", reply)

    def finish_worker(self):
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

class DiaryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        title = QLabel("Sustainability Diary")
        title.setObjectName("PageTitleLabel")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)
        box = QLabel("Your diary goes here. (Placeholder — UI preserved)")
        box.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY};")
        layout.addWidget(box)
        layout.addStretch()

class AnalyzeDocPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        title = QLabel("Analyze Document")
        title.setObjectName("PageTitleLabel")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)
        box = QLabel("Document analysis UI here. (Placeholder — UI preserved)")
        box.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY};")
        layout.addWidget(box)
        layout.addStretch()

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        title = QLabel("Settings")
        title.setObjectName("PageTitleLabel")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)
        box = QLabel("Settings UI here. (Placeholder — UI preserved)")
        box.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY};")
        layout.addWidget(box)
        layout.addStretch()

# =========================
# Main window
# =========================
class GreenLensDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GreenLens")
        self.setFixedSize(1280, 780)
        self.setStyleSheet(f"background-color: {COLOR_BACKGROUND};")

        self.central_widget = QWidget()
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.nav_menu = self._create_nav_menu()

        self.stacked_widget = QStackedWidget()
        self.dashboard_page = self._create_dashboard_page()
        self.scan_page_instance = ScanPage(self)
        self.diary_page = DiaryPage(self)
        self.chat_page = ChatPage(self)
        self.doc_page = AnalyzeDocPage(self)
        self.settings_page = SettingsPage(self)

        self.stacked_widget.addWidget(self.dashboard_page)     # 0
        self.stacked_widget.addWidget(self.scan_page_instance) # 1
        self.stacked_widget.addWidget(self.diary_page)         # 2
        self.stacked_widget.addWidget(self.chat_page)          # 3
        self.stacked_widget.addWidget(self.doc_page)           # 4
        self.stacked_widget.addWidget(self.settings_page)      # 5

        self.main_layout.addWidget(self.nav_menu)
        self.main_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(self.central_widget)

        self._create_floating_ai_button()
        self.stacked_widget.setCurrentIndex(0)
        self._set_active("Dashboard")

    def _create_floating_ai_button(self):
        self.ai_button = QPushButton("Ai", self)
        self.ai_button.setObjectName("AIFloatingButton")
        self.ai_button.setFixedSize(60, 60)
        self.ai_button.move(self.width() - 90, self.height() - 90)

    def _create_nav_menu(self):
        nav_widget = QWidget()
        nav_widget.setObjectName("NavMenu")
        nav_widget.setFixedWidth(220)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(20, 20, 10, 20)
        nav_layout.setSpacing(8)

        logo_layout = QHBoxLayout()
        logo_icon_label = QLabel()
        try:
            logo_icon_label.setPixmap(QIcon("icons/tea.png").pixmap(24, 24))
        except Exception:
            logo_icon_label.setText("🍃")
        logo_text_label = QLabel("GreenLens")
        logo_text_label.setObjectName("LogoLabel")
        logo_layout.addWidget(logo_icon_label)
        logo_layout.addWidget(logo_text_label)
        logo_layout.addStretch()
        nav_layout.addLayout(logo_layout)
        nav_layout.addSpacing(30)

        container = QFrame()
        container.setObjectName("NavButtonsContainer")
        v = QVBoxLayout(container)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(5)

        nav_buttons_data = [
            ("Dashboard", "icons/dashboard.png", False),
            ("Scan Product", "icons/qrcode.png", False),
            ("Sustainability Diary", "icons/diary.png", False),
            ("AI Chat", "icons/bubblechat.png", False),
            ("Analyze Document", "icons/googledocs.png", False),
            ("Settings", "icons/setting.png", False)
        ]
        self.nav_buttons = {}
        for text, icon_path, is_active in nav_buttons_data:
            btn = NavButton(text, icon_path, is_active)
            self.nav_buttons[text] = btn
            v.addWidget(btn)

        nav_layout.addWidget(container)
        nav_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        logout_btn = NavButton("Logout", "icons/logout.png", False)
        self.nav_buttons["Logout"] = logout_btn
        nav_layout.addWidget(logout_btn)
        nav_layout.addSpacing(15)

        ellipsis_btn = QPushButton("…")
        ellipsis_btn.setObjectName("EllipsisButton")
        ellipsis_btn.setFixedSize(40, 40)
        nav_layout.addWidget(ellipsis_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # routing
        self.nav_buttons["Dashboard"].clicked.connect(lambda: self._route("Dashboard"))
        self.nav_buttons["Scan Product"].clicked.connect(lambda: self._route("Scan Product"))
        self.nav_buttons["Sustainability Diary"].clicked.connect(lambda: self._route("Sustainability Diary"))
        self.nav_buttons["AI Chat"].clicked.connect(lambda: self._route("AI Chat"))
        self.nav_buttons["Analyze Document"].clicked.connect(lambda: self._route("Analyze Document"))
        self.nav_buttons["Settings"].clicked.connect(lambda: self._route("Settings"))
        self.nav_buttons["Logout"].clicked.connect(self.close)

        return nav_widget

    def _set_active(self, name: str):
        for n, btn in self.nav_buttons.items():
            active = (n == name)
            btn.setProperty("active", active)
            btn.setChecked(active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _route(self, name: str):
        index_map = {
            "Dashboard": 0,
            "Scan Product": 1,
            "Sustainability Diary": 2,
            "AI Chat": 3,
            "Analyze Document": 4,
            "Settings": 5,
        }
        if name in index_map:
            self.stacked_widget.setCurrentIndex(index_map[name])
            self._set_active(name)

    def _create_card(self, object_name):
        card = QFrame()
        card.setObjectName(object_name)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMinimumHeight(200)
        return card

    def _create_sustainability_card(self):
        card = self._create_card("InfoCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Sustainability Diary")
        title.setObjectName("CardTitle")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)

        progress_bar = CircularProgressBar()
        layout.addWidget(progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        eco_streak_label = QLabel("● 7 Day Eco-Streak")
        eco_streak_label.setObjectName("StatLabel")
        stats_layout.addWidget(eco_streak_label)
        zero_waste_label = QLabel("● Zero-Waste Hero")
        zero_waste_label.setObjectName("StatLabel")
        stats_layout.addWidget(zero_waste_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        return card

    def _create_copilot_card(self):
        card = self._create_card("InfoCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_layout = QHBoxLayout()
        icon_label = QLabel("💡")
        icon_label.setFont(QFont("Segoe UI Emoji", 16))
        icon_label.setStyleSheet(f"color: {COLOR_ACCENT_AI};")
        title = QLabel("Copilot Tip")
        title.setObjectName("CardTitle")
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        tip_text = QLabel("Try swapping beef for lentils once\na week. Save ~3kg CO₂e!")
        tip_text.setObjectName("CardContent")
        tip_text.setWordWrap(True)
        layout.addWidget(tip_text)

        progress_container = QFrame()
        progress_container.setFixedHeight(5)
        progress_container.setStyleSheet(f"""
            QFrame {{ background-color: {COLOR_CARD_BORDER}; border-radius: 2px; }}
        """)
        layout.addWidget(progress_container)

        inner = QHBoxLayout(progress_container); inner.setContentsMargins(0,0,0,0)
        filled = QFrame(); filled.setStyleSheet(f"background-color:{COLOR_PRIMARY_GREEN}; border-top-left-radius:2px; border-bottom-left-radius:2px;")
        empty = QFrame(); empty.setStyleSheet("background-color: transparent; border-top-right-radius:2px; border-bottom-right-radius:2px;")
        inner.addWidget(filled, 7); inner.addWidget(empty, 3)

        layout.addStretch()
        return card

    def _create_quick_actions_card(self):
        card = self._create_card("QuickActionsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Quick Actions")
        title.setObjectName("CardTitle")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)

        row = QHBoxLayout(); row.setSpacing(20)

        scan_btn = QPushButton("Scan Product - On-Device AI")
        scan_btn.setObjectName("ScanButton")
        try: scan_btn.setIcon(QIcon("icons/camera.png"))
        except Exception: scan_btn.setIcon(QIcon())
        scan_btn.setIconSize(QSize(20, 20))
        scan_btn.setMinimumHeight(60)

        analyze_btn = QPushButton("Analyze Document")
        analyze_btn.setObjectName("AnalyzeButton")
        try: analyze_btn.setIcon(QIcon("icons/googledocs.png"))
        except Exception: analyze_btn.setIcon(QIcon())
        analyze_btn.setIconSize(QSize(20, 20))
        analyze_btn.setMinimumHeight(60)

        row.addWidget(scan_btn); row.addWidget(analyze_btn)
        layout.addLayout(row)

        scan_btn.clicked.connect(lambda: self._route("Scan Product"))
        analyze_btn.clicked.connect(lambda: self._route("Analyze Document"))
        return card

    def _create_dashboard_page(self):
        w = QWidget()
        content = QVBoxLayout(w)
        content.setContentsMargins(40, 30, 40, 40)
        content.setSpacing(25)

        title = QLabel("Main Dashboard / Home Page")
        title.setObjectName("PageTitleLabel")
        content.addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)

        top = QHBoxLayout(); top.setSpacing(30)
        top.addWidget(self._create_sustainability_card(), 1)
        top.addWidget(self._create_copilot_card(), 1)
        content.addLayout(top)
        content.addSpacing(30)
        content.addWidget(self._create_quick_actions_card())
        content.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        return w

# =========================
# App bootstrap + styles
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(f"""
        QWidget {{
            color: {COLOR_TEXT_PRIMARY};
            font-family: "Segoe UI", sans-serif;
        }}
        QMainWindow {{ background-color: {COLOR_BACKGROUND}; }}
        #NavMenu {{ background-color: {COLOR_NAV_MENU}; border-right: 1px solid {COLOR_CARD_BORDER}; }}
        #ContentArea, QStackedWidget {{ background-color: {COLOR_CONTENT_AREA}; }}

        #LogoLabel {{ font-size: 20px; font-weight: 700; color: {COLOR_TEXT_PRIMARY}; padding-left: 5px; }}

        #InfoCard, #QuickActionsCard {{
            background-color: {COLOR_CARD_BACKGROUND};
            border: 1px solid {COLOR_PRIMARY_GREEN};
            border-radius: 12px;
        }}
        #NavButtonsContainer {{
            background-color: {COLOR_CARD_BACKGROUND};
            border: 1px solid {COLOR_PRIMARY_GREEN};
            border-radius: 12px;
            margin-top: 15px; margin-bottom: 15px;
        }}

        #NavButton {{
            background-color: transparent; border: none; padding: 10px 15px;
            font-size: 14px; text-align: left; border-radius: 8px; color: {COLOR_TEXT_SECONDARY};
        }}
        #NavButton:hover {{ background-color: {COLOR_CARD_BACKGROUND}; color: {COLOR_TEXT_PRIMARY}; }}
        #NavButton[active="true"] {{
            background-color: {COLOR_CARD_BACKGROUND}; color: {COLOR_TEXT_PRIMARY}; font-weight: 600; position: relative;
        }}
        #NavButton[active="true"]::before {{
            content: ""; position: absolute; top: 0; right: 0; bottom: 0; width: 5px;
            background-color: {COLOR_ACTIVE_NAV_BAR}; border-top-right-radius: 3px; border-bottom-right-radius: 3px;
        }}
        #NavButton::menu-indicator {{ image: none; }}

        #EllipsisButton {{
            background-color: {COLOR_CARD_BACKGROUND};
            border: 1px solid {COLOR_CARD_BORDER};
            border-radius: 12px;
            color: {COLOR_TEXT_SECONDARY};
            font-size: 18px; font-weight: bold; padding: 0;
        }}
        #EllipsisButton:hover {{ background-color: #3c3c3c; }}

        #PageTitleLabel {{ font-size: 24px; font-weight: 300; color: {COLOR_TEXT_PRIMARY}; }}
        #CardTitle {{ font-size: 18px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; margin-bottom: 5px; }}
        #StatLabel {{ font-size: 13px; color: {COLOR_TEXT_SECONDARY}; }}
        #CardContent {{ font-size: 14px; color: {COLOR_TEXT_SECONDARY}; line-height: 1.5; }}

        #ScanButton {{
            padding: 15px 25px; font-size: 16px; font-weight: 600; border-radius: 10px; text-align: center;
            background-color: transparent; border: 1px solid {COLOR_PRIMARY_GREEN}; color: {COLOR_TEXT_PRIMARY};
        }}
        #ScanButton:hover {{ background-color: rgba(76, 175, 80, 0.1); border: 1px solid {COLOR_ACTIVE_NAV_BAR}; }}
        #AnalyzeButton {{
            padding: 15px 25px; font-size: 16px; font-weight: 600; border-radius: 10px; text-align: center;
            background-color: {COLOR_PRIMARY_GREEN}; border: 1px solid {COLOR_PRIMARY_GREEN}; color: #FFFFFF;
        }}
        #AnalyzeButton:hover {{ background-color: {COLOR_ACCENT_AI}; border: 1px solid {COLOR_ACCENT_AI}; }}

        #AIFloatingButton {{
            background-color: {COLOR_ACCENT_AI}; color: {COLOR_BACKGROUND};
            font-size: 20px; font-weight: bold; border-radius: 30px; border: 2px solid {COLOR_BACKGROUND};
        }}

        #CameraViewContainer {{
            background-color: #000000;
            border: 1px solid {COLOR_PRIMARY_GREEN};
            border-radius: 12px;
        }}
        #CameraFeedLabel {{ color: {COLOR_TEXT_SECONDARY}; font-size: 16px; }}

        QLineEdit {{
            background-color: {COLOR_CARD_BACKGROUND}; border: 1px solid {COLOR_CARD_BORDER};
            border-radius: 8px; padding: 10px; color: {COLOR_TEXT_PRIMARY}; font-size: 14px;
        }}
        QLineEdit:focus {{ border: 1px solid {COLOR_PRIMARY_GREEN}; }}
    """)
    window = GreenLensDashboard()
    window.show()
    sys.exit(app.exec())

