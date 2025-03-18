#!/usr/bin/env python3
import os
import json
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QListWidget, QListWidgetItem, QHBoxLayout, 
    QVBoxLayout, QWidget, QCheckBox, QToolButton, QLabel, QMenu, QPushButton,
    QLineEdit
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QFont, QColor, QIcon
import pyperclip
import sys

STATE_FILE = "state.json"
DEFAULT_OPACITY = 0.85

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
        self.is_editing = False
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.context_checkbox = DragSelectableCheckBox()
        self.layout.addWidget(self.context_checkbox)
        
        if is_link:
            self.link_indicator = QLabel()
            self.link_indicator.setFixedSize(12, 12)
            self.link_indicator.setStyleSheet("background-color: #00aa00; border-radius: 6px;")
            self.link_indicator.setToolTip(f"Live Link: {link_path}")
            self.layout.addWidget(self.link_indicator)
            
        self.name_label = QLabel(item_name)
        self.name_edit = QLineEdit(item_name)
        self.name_edit.hide()
        self.name_edit.returnPressed.connect(self.finish_editing)
        self.name_edit.editingFinished.connect(self.cancel_editing)
        
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.name_edit)
        self.layout.addStretch()

    def start_editing(self):
        self.is_editing = True
        self.name_label.hide()
        # Remove 📎 prefix for editing if it exists
        edit_text = self.item_name[2:] if self.item_name.startswith("📎 ") else self.item_name
        self.name_edit.setText(edit_text)
        self.name_edit.show()
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def finish_editing(self):
        if self.is_editing:
            new_name = self.name_edit.text().strip()
            if new_name and new_name != self.item_name:
                old_name = self.item_name
                # Add 📎 prefix if it's a clipboard item (not a link)
                if not self.is_link:
                    new_name = f"📎 {new_name}"
                self.item_name = new_name
                self.name_label.setText(new_name)
                self.parent().parent().main_window.update_item_name(old_name, self.is_link, new_name)
            self.name_edit.hide()
            self.name_label.show()
            self.is_editing = False

    def cancel_editing(self):
        if self.is_editing:
            self.name_edit.hide()
            self.name_label.show()
            self.is_editing = False

class DroppableListWidget(QListWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.itemDoubleClicked.connect(self.handle_double_click)

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

    def handle_double_click(self, item):
        widget = self.itemWidget(item)
        # Allow renaming for any non-link item (original clipboard items or renamed ones)
        if widget and not widget.is_link:
            widget.start_editing()

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
                goto_action = menu.addAction("Go to Directory") if widget.is_link else None
                action = menu.exec(self.mapToGlobal(pos))
                if action == remove_action:
                    self.main_window.remove_item(widget.item_name, widget.is_link)
                elif action == goto_action and widget.is_link:
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

class OpacityControl(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedSize(20, 20)
        self.setStyleSheet("background-color: #d0d0d0; border: 1px solid #808080; border-radius: 3px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("👻")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setToolTip("Scroll to adjust opacity (15%–100%)")

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        current_opacity = self.main_window.windowOpacity()
        step = 0.05
        new_opacity = current_opacity + (step if delta > 0 else -step)
        new_opacity = max(0.15, min(1.0, new_opacity))
        self.main_window.setWindowOpacity(new_opacity)
        self.main_window.save_state()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ContextYap")
        self.setWindowIcon(QIcon("icon.jpg"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        state = self.load_state()
        self.items = state.get("items", [])
        saved_opacity = state.get("opacity", DEFAULT_OPACITY)
        saved_width = state.get("width", 200)
        saved_height = state.get("height", 400)
        self.setWindowOpacity(saved_opacity)
        self.resize(saved_width, saved_height)
        
        header_layout = QHBoxLayout()
        self.top_toggle = QToolButton()
        self.top_toggle.setText("📌")
        self.top_toggle.setMaximumWidth(30)
        self.top_toggle.setCheckable(True)
        self.top_toggle.setChecked(True)
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
        
        self.collapse_button = QToolButton()
        self.collapse_button.setText("▲")
        self.collapse_button.setMaximumWidth(20)
        self.collapse_button.setStyleSheet("QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }")
        self.collapse_button.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.collapse_button)
        
        self.opacity_control = OpacityControl(self)
        header_layout.addWidget(self.opacity_control)
        
        self.clipboard_button = QPushButton("📎")
        self.clipboard_button.setFixedWidth(20)
        self.clipboard_button.setStyleSheet("QPushButton { background: transparent; color: white; border: 1px solid #808080; padding: 5px; }")
        self.clipboard_button.clicked.connect(self.add_clipboard_cold_link)
        header_layout.addWidget(self.clipboard_button)
        
        header_layout.addStretch()
        self.file_drop_area = FileDropArea(self)
        header_layout.addWidget(self.file_drop_area)
        
        self.list_widget = DroppableListWidget(self)
        self.is_collapsed = False
        self.previous_height = saved_height
        for item in self.items:
            self.add_item_to_list(item["name"], item.get("is_link", False), item.get("link_path"), item.get("checked", False))
        
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.is_collapsed:
            self.save_state()

    def process_file_drop(self, file_path, is_link):
        base_name = os.path.basename(file_path)
        name, _ = os.path.splitext(base_name)
        if not any(item["name"] == name and item.get("is_link", False) == is_link for item in self.items):
            if is_link:
                item_data = {"name": name, "is_link": True, "link_path": os.path.abspath(file_path), "checked": False}
            else:
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                except Exception as e:
                    content = f"[Error reading file: {e}]"
                item_data = {"name": name, "is_link": False, "content": content, "checked": False}
            self.items.append(item_data)
            self.add_item_to_list(name, is_link, os.path.abspath(file_path) if is_link else None, False)
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

    def update_item_name(self, old_name, is_link, new_name):
        item_data = next((item for item in self.items if item["name"] == old_name and item.get("is_link", False) == is_link), None)
        if item_data and not any(item["name"] == new_name for item in self.items if item != item_data):
            item_data["name"] = new_name
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
                item_data = next((item for item in self.items if item["name"] == widget.item_name and item.get("is_link", False) == widget.is_link), None)
                if item_data:
                    if widget.is_link:
                        file_path = widget.link_path
                        try:
                            with open(file_path, "r") as f:
                                content = f.read()
                        except Exception as e:
                            content = f"[Error: {e}]"
                        formatted_text.append(f"{file_path}")
                    else:
                        content = item_data.get("content", "[No content available]")
                        formatted_text.append(f"{widget.item_name}")
                    formatted_text.append("```")
                    formatted_text.append(content)
                    formatted_text.append("```")
                    formatted_text.append("")
        if formatted_text:
            result = "\n".join(formatted_text)
            pyperclip.copy(result)

    def add_clipboard_cold_link(self):
        clipboard_text = pyperclip.paste().strip()
        if clipboard_text:
            clipboard_count = sum(1 for item in self.items if item["name"].startswith("clipboard-") or item["name"].startswith("📎 ")) + 1
            name = f"clipboard-{clipboard_count}"
            if not any(item["name"] == name for item in self.items):
                item_data = {"name": name, "is_link": False, "content": clipboard_text, "checked": False}
                self.items.append(item_data)
                self.add_item_to_list(name, False, None, False)
                self.save_state()

    def toggle_always_on_top(self):
        current_flags = self.windowFlags()
        if self.top_toggle.isChecked():
            self.setWindowFlags(current_flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(current_flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_collapse(self):
        if self.is_collapsed:
            self.list_widget.show()
            self.collapse_button.setText("▲")
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.resize(self.width(), self.previous_height)
            self.is_collapsed = False
        else:
            self.previous_height = self.height()
            self.list_widget.hide()
            self.collapse_button.setText("▼")
            header_height = 40 + self.frameGeometry().height() - self.geometry().height()
            self.setFixedHeight(header_height)
            self.is_collapsed = True
        self.save_state()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {"items": [], "opacity": DEFAULT_OPACITY, "width": 200, "height": 200}

    def save_state(self):
        state = {
            "items": self.items,
            "opacity": self.windowOpacity(),
            "width": self.width(),
            "height": self.height() if not self.is_collapsed else self.previous_height
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()