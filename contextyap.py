#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from logic import MainWindowLogic, DroppableListWidget, FileDropArea, OpacityControl, DEFAULT_OPACITY, STATE_FILE

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logic = MainWindowLogic(self)
        self.setup_ui()
        self.load_initial_state()

    def _create_button(self, text, width, style, callback, checkable=False):
        btn = QToolButton() if checkable or width <= 30 else QPushButton()
        btn.setText(text)
        btn.setMaximumWidth(width)
        btn.setStyleSheet(style)
        btn.clicked.connect(callback)
        if checkable:
            btn.setCheckable(True)
            btn.setChecked(True)
        return btn

    def setup_ui(self):
        self.setWindowTitle("ContextYap")
        self.setWindowIcon(QIcon("icon.jpg"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Header layout with buttons
        header_layout = QHBoxLayout()
        button_configs = [
            ("📌", 30, "QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; } QToolButton:checked { background: #ffaa00; color: white; }", self.logic.toggle_always_on_top, True),
            ("CC", 30, "QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }", self.logic.clear_context),
            ("C", 20, "QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }", self.logic.copy_context),
            ("▲", 20, "QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }", self.logic.toggle_collapse),
            ("📎", 20, "QPushButton { background-color: #4d4d4d; color: white; border: 1px solid #808080; padding: 5px; }", self.logic.add_clipboard_cold_link),
        ]
        self.top_toggle, self.cc_button, self.c_button, self.collapse_button, self.clipboard_button = [
            self._create_button(*config) for config in button_configs
        ]
        self.opacity_control = OpacityControl(self)  # Moved outside the tuple
        for btn in (self.top_toggle, self.cc_button, self.c_button, self.collapse_button, self.opacity_control, self.clipboard_button):
            header_layout.addWidget(btn)

        header_layout.addStretch()
        self.file_drop_area = FileDropArea(self)
        header_layout.addWidget(self.file_drop_area)

        # Main layout
        self.list_widget = DroppableListWidget(self)
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setFixedHeight(40)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header_widget)
        main_layout.addWidget(self.list_widget)
        self.setCentralWidget(central_widget)

    def load_initial_state(self):
        state = self.logic.load_state()
        self.setWindowOpacity(state.get("opacity", DEFAULT_OPACITY))
        self.resize(state.get("width", 200), state.get("height", 400))
        for item in state.get("items", []):
            self.logic.add_item_to_list(item["name"], item.get("is_link", False), item.get("link_path"), item.get("checked", False))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.logic.is_collapsed:
            self.logic.save_state()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()