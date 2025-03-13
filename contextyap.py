#!/usr/bin/env python3
import os
import json
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QListWidget, QListWidgetItem, QHBoxLayout, 
    QVBoxLayout, QWidget, QCheckBox, QToolButton, QLabel, QMenu
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QFont, QColor, QIcon
import pyperclip
import sys

STATE_FILE = "state.json"

class DragSelectableCheckBox(QCheckBox):
    _drag_active = False
    _target_state = None

    def __init__(self, parent=None):
        super().__init__(parent)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.setStyleSheet("""
            QCheckBox::indicator { background-color: grey; border: 1px solid black; width: 15px; height: 15px; }
            QCheckBox::indicator:checked { background-color: lightblue; }
        """)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease:
            DragSelectableCheckBox._drag_active = False
            DragSelectableCheckBox._target_state = None
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            DragSelectableCheckBox._drag_active = True
            DragSelectableCheckBox._target_state = not self.isChecked()
            self.setChecked(DragSelectableCheckBox._target_state)
            event.accept()
        else:
            super().mousePressEvent(event)

class IdeaItemWidget(QWidget):
    def __init__(self, item_name, is_link=False, link_path=None, parent=None):
        super().__init__(parent)
        self.item_name = item_name
        self.is_link = is_link
        self.link_path = link_path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.context_checkbox = DragSelectableCheckBox()
        layout.addWidget(self.context_checkbox)
        if is_link:
            self.link_indicator = QLabel()
            self.link_indicator.setFixedSize(12, 12)
            self.link_indicator.setStyleSheet("background-color: #00aa00; border-radius: 6px;")
            self.link_indicator.setToolTip(f"Live Link: {link_path}")
            layout.addWidget(self.link_indicator)
        self.name_label = QLabel(item_name)
        # Removed green text for linked items; all text uses default color
        layout.addWidget(self.name_label)
        layout.addStretch()

class DroppableListWidget(QListWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path:
                    self.main_window.process_file_drop(file_path, is_link=False)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def mouseMoveEvent(self, event):
        if DragSelectableCheckBox._drag_active and DragSelectableCheckBox._target_state is not None:
            pos = event.pos()
            item = self.itemAt(pos)
            if item:
                widget = self.itemWidget(item)
                if widget and isinstance(widget, IdeaItemWidget):
                    checkbox = widget.context_checkbox
                    if checkbox.isChecked() != DragSelectableCheckBox._target_state:
                        checkbox.setChecked(DragSelectableCheckBox._target_state)
                        self.main_window.update_item_state(widget.item_name, widget.is_link, DragSelectableCheckBox._target_state)
        super().mouseMoveEvent(event)

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item:
            widget = self.itemWidget(item)
            selected_items = self.selectedItems()
            if len(selected_items) > 1 and item in selected_items:
                menu = QMenu(self)
                remove_action = menu.addAction("Remove Selected")
                action = menu.exec(self.mapToGlobal(pos))
                if action == remove_action:
                    for selected_item in selected_items:
                        selected_widget = self.itemWidget(selected_item)
                        self.main_window.remove_item(selected_widget.item_name, selected_widget.is_link)
            else:
                menu = QMenu(self)
                remove_action = menu.addAction("Remove")
                goto_action = menu.addAction("Go to Directory")
                action = menu.exec(self.mapToGlobal(pos))
                if action == remove_action:
                    self.main_window.remove_item(widget.item_name, widget.is_link)
                elif action == goto_action:
                    self.main_window.go_to_directory(widget.item_name, widget.is_link)

class FileDropArea(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAcceptDrops(True)
        self.setFixedSize(30, 30)
        self.setStyleSheet("""
            QWidget { background-color: #e0e0e0; border: 1px dashed #808080; border-radius: 5px; }
            QWidget:hover { background-color: #c0c0c0; border: 1px solid #404040; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        label = QLabel("🔗")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setToolTip("Drop files here for live links")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path:
                    self.main_window.process_file_drop(file_path, is_link=True)
            event.acceptProposedAction()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ContextYap")
        self.setWindowIcon(QIcon("icon.jpg"))  # Updated to use "icon.jpg"
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # Start with Always on Top
        self.resize(600, 400)
        self.items = self.load_state()
        header_layout = QHBoxLayout()
        self.top_toggle = QToolButton()
        self.top_toggle.setText("📌")
        self.top_toggle.setMaximumWidth(30)
        self.top_toggle.setCheckable(True)
        self.top_toggle.setChecked(True)  # Pin button starts checked
        self.top_toggle.setStyleSheet("""
            QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }
            QToolButton:checked { background: #ffaa00; color: white; }
        """)
        self.top_toggle.clicked.connect(self.toggle_always_on_top)
        header_layout.addWidget(self.top_toggle)
        self.cc_button = QToolButton()
        self.cc_button.setText("CC")
        self.cc_button.setMaximumWidth(30)
        self.cc_button.setStyleSheet("QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }")
        self.cc_button.clicked.connect(self.clear_context)
        header_layout.addWidget(self.cc_button)
        self.c_button = QToolButton()
        self.c_button.setText("C")
        self.c_button.setMaximumWidth(20)
        self.c_button.setStyleSheet("QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }")
        self.c_button.clicked.connect(self.copy_context)
        header_layout.addWidget(self.c_button)
        header_layout.addStretch()
        self.file_drop_area = FileDropArea(self)
        header_layout.addWidget(self.file_drop_area)
        self.list_widget = DroppableListWidget(self)
        for item in self.items:
            self.add_item_to_list(item["name"], item.get("is_link", False), item.get("link_path"), item.get("checked", False))
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.list_widget)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def process_file_drop(self, file_path, is_link):
        base_name = os.path.basename(file_path)
        name, _ = os.path.splitext(base_name)
        if any(item["name"] == name for item in self.items):
            return
        item_data = {"name": name, "is_link": is_link, "link_path": os.path.abspath(file_path), "checked": False}
        self.items.append(item_data)
        self.add_item_to_list(name, is_link, os.path.abspath(file_path), False)
        self.save_state()

    def add_item_to_list(self, name, is_link, link_path=None, checked=False):
        widget = IdeaItemWidget(name, is_link, link_path)
        widget.context_checkbox.setChecked(checked)
        list_item = QListWidgetItem()
        list_item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(list_item)
        self.list_widget.setItemWidget(list_item, widget)

    def remove_item(self, name, is_link):
        item_data = next((item for item in self.items if item["name"] == name and item.get("is_link", False) == is_link), None)
        if item_data:
            self.items.remove(item_data)
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if widget.item_name == name and widget.is_link == is_link:
                self.list_widget.takeItem(i)
                break
        self.save_state()

    def update_item_state(self, name, is_link, checked):
        item_data = next((item for item in self.items if item["name"] == name and item.get("is_link", False) == is_link), None)
        if item_data:
            item_data["checked"] = checked
            self.save_state()

    def go_to_directory(self, name, is_link):
        path = self.get_item_path(name, is_link)
        if os.path.exists(path):
            if sys.platform == "win32":
                os.startfile(os.path.dirname(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", os.path.dirname(path)])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])

    def get_item_path(self, name, is_link):
        return next(item["link_path"] for item in self.items if item["name"] == name and item.get("is_link", False) == is_link)

    def clear_context(self):
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            widget.context_checkbox.setChecked(False)
            self.update_item_state(widget.item_name, widget.is_link, False)

    def copy_context(self):
        formatted_text = []
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if widget.context_checkbox.isChecked():
                file_path = widget.link_path
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                    formatted_text.append(f"{file_path}")
                    formatted_text.append("```")
                    formatted_text.append(content)
                    formatted_text.append("```")
                    formatted_text.append("")
                except Exception as e:
                    formatted_text.append(f"{file_path}")
                    formatted_text.append("```")
                    formatted_text.append(f"[Error: {e}]")
                    formatted_text.append("```")
                    formatted_text.append("")
        if formatted_text:
            result = "\n".join(formatted_text)
            pyperclip.copy(result)

    def toggle_always_on_top(self):
        current_flags = self.windowFlags()
        if self.top_toggle.isChecked():
            self.setWindowFlags(current_flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(current_flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f).get("items", [])
        return []

    def save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump({"items": self.items}, f, indent=4)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()