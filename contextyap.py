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

    def setup_ui(self):
        self.setWindowTitle("ContextYap")
        self.setWindowIcon(QIcon("icon.jpg"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Header layout
        header_layout = QHBoxLayout()
        self.top_toggle = QToolButton()
        self.top_toggle.setText("📌")
        self.top_toggle.setMaximumWidth(30)
        self.top_toggle.setCheckable(True)
        self.top_toggle.setChecked(True)
        self.top_toggle.setStyleSheet("QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; } QToolButton:checked { background: #ffaa00; color: white; }")
        self.top_toggle.clicked.connect(self.logic.toggle_always_on_top)
        header_layout.addWidget(self.top_toggle)

        self.cc_button = QToolButton()
        self.cc_button.setText("CC")
        self.cc_button.setMaximumWidth(30)
        self.cc_button.setStyleSheet("QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }")
        self.cc_button.clicked.connect(self.logic.clear_context)
        header_layout.addWidget(self.cc_button)

        self.c_button = QToolButton()
        self.c_button.setText("C")
        self.c_button.setMaximumWidth(20)
        self.c_button.setStyleSheet("QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }")
        self.c_button.clicked.connect(self.logic.copy_context)
        header_layout.addWidget(self.c_button)

        self.collapse_button = QToolButton()
        self.collapse_button.setText("▲")
        self.collapse_button.setMaximumWidth(20)
        self.collapse_button.setStyleSheet("QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }")
        self.collapse_button.clicked.connect(self.logic.toggle_collapse)
        header_layout.addWidget(self.collapse_button)

        self.opacity_control = OpacityControl(self)
        header_layout.addWidget(self.opacity_control)

        self.clipboard_button = QPushButton("📎")
        self.clipboard_button.setFixedWidth(20)
        self.clipboard_button.setStyleSheet("QPushButton { background-color: #4d4d4d; color: white; border: 1px solid #808080; padding: 5px; }")
        self.clipboard_button.clicked.connect(self.logic.add_clipboard_cold_link)
        header_layout.addWidget(self.clipboard_button)

        header_layout.addStretch()
        self.file_drop_area = FileDropArea(self)
        header_layout.addWidget(self.file_drop_area)

        # Main layout
        self.list_widget = DroppableListWidget(self)
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setFixedHeight(40)

        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header_widget)
        main_layout.addWidget(self.list_widget)
        central_widget.setLayout(main_layout)
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