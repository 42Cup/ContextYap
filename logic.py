import os
import json
import subprocess
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QCheckBox, QHBoxLayout, QLabel, QMenu, QLineEdit, QApplication
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor
import pyperclip

STATE_FILE = "state.json"
DEFAULT_OPACITY = 0.85
TEXT_EXTENSIONS = {'.js', '.md'}
BLOCKED_DIRECTORIES = ['src/locale']

def read_file_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[Error: {e}]"

def open_directory(path):
    if os.path.exists(path):
        cmd = {"win32": os.startfile, "darwin": lambda p: subprocess.Popen(["open", p]), "linux": lambda p: subprocess.Popen(["xdg-open", p])}
        cmd.get(sys.platform, lambda p: None)(os.path.dirname(path))

class DragSelectableCheckBox(QCheckBox):
    _drag_active = False
    _target_state = None

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        if app := main_window.logic.app:
            app.installEventFilter(self)
        self.setStyleSheet("QCheckBox::indicator { background-color: grey; border: 1px solid black; width: 15px; height: 15px; } QCheckBox::indicator:checked { background-color: lightblue; }")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease:
            DragSelectableCheckBox._drag_active = DragSelectableCheckBox._target_state = None
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            current_time = event.timestamp()
            if hasattr(self, '_last_click_time') and (current_time - self._last_click_time < 300):
                self.main_window.logic.clear_context()
            else:
                DragSelectableCheckBox._drag_active, DragSelectableCheckBox._target_state = True, not self.isChecked()
                self.setChecked(DragSelectableCheckBox._target_state)
            self._last_click_time = current_time
            event.accept()

class IdeaItemWidget(QWidget):
    def __init__(self, item_name, is_link=False, link_path=None, main_window=None, parent=None):
        super().__init__(parent)
        self.item_name, self.is_link, self.link_path, self.main_window, self.is_editing = item_name, is_link, link_path, main_window, False
        self.setup_ui()

    def setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.context_checkbox = DragSelectableCheckBox(self.main_window)
        self.layout.addWidget(self.context_checkbox)

        if self.is_link:
            self.link_indicator = QLabel()
            self.link_indicator.setFixedSize(12, 12)
            self.link_indicator.setStyleSheet("background-color: #00aa00; border-radius: 6px;")
            self.link_indicator.setToolTip(f"Live Link: {self.link_path}")
            self.layout.addWidget(self.link_indicator)

        self.name_label, self.name_edit = QLabel(self.item_name), QLineEdit(self.item_name)
        self.name_edit.hide()
        self.name_edit.returnPressed.connect(self.finish_editing)
        self.name_edit.editingFinished.connect(self.cancel_editing)
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.name_edit)
        self.layout.addStretch()

    def start_editing(self):
        self.is_editing = True
        self.name_label.hide()
        self.name_edit.setText(self.item_name[2:] if self.item_name.startswith("📎 ") else self.item_name)
        self.name_edit.show()
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def finish_editing(self):
        if self.is_editing and (new_name := self.name_edit.text().strip()) and new_name != self.item_name:
            old_name = self.item_name
            self.item_name = f"📎 {new_name}" if not self.is_link else new_name
            self.name_label.setText(self.item_name)
            self.main_window.logic.update_item_name(old_name, self.is_link, self.item_name)
        self.cancel_editing()

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
        self.drag_origin = None  # Track drag origin: 'checkbox' or 'body'

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path:
                    (self.main_window.logic.process_folder_drop if os.path.isdir(path) else self.main_window.logic.process_file_drop)(path, is_link=False)
            event.acceptProposedAction()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if item:
            widget = self.itemWidget(item)
            if widget and isinstance(widget, IdeaItemWidget):
                checkbox_rect = widget.context_checkbox.geometry()
                if checkbox_rect.contains(widget.mapFromGlobal(event.globalPos())):
                    self.drag_origin = 'checkbox'
                    # Sync with DragSelectableCheckBox state
                    DragSelectableCheckBox._drag_active = True
                    DragSelectableCheckBox._target_state = not widget.context_checkbox.isChecked()
                    widget.context_checkbox.setChecked(DragSelectableCheckBox._target_state)
                    self.main_window.logic.update_item_state(widget.item_name, widget.is_link, DragSelectableCheckBox._target_state)
                else:
                    self.drag_origin = 'body'

    def mouseMoveEvent(self, event):
        if DragSelectableCheckBox._drag_active and DragSelectableCheckBox._target_state is not None and (item := self.itemAt(event.pos())):
            widget = self.itemWidget(item)
            if widget and isinstance(widget, IdeaItemWidget):
                if self.drag_origin == 'checkbox':
                    # Toggle checkboxes when dragging over them
                    if widget.context_checkbox.isChecked() != DragSelectableCheckBox._target_state:
                        widget.context_checkbox.setChecked(DragSelectableCheckBox._target_state)
                        self.main_window.logic.update_item_state(widget.item_name, widget.is_link, DragSelectableCheckBox._target_state)
                elif self.drag_origin == 'body':
                    # Select list items when dragging over body
                    self.setCurrentItem(item)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def handle_double_click(self, item):
        if (widget := self.itemWidget(item)) and not widget.is_link:
            widget.start_editing()

    def show_context_menu(self, pos):
        if item := self.itemAt(pos):
            widget, selected_items = self.itemWidget(item), self.selectedItems()
            menu = QMenu(self)
            is_multi_select = len(selected_items) > 1 and item in selected_items
            remove_action = menu.addAction("Remove Selected" if is_multi_select else "Remove")
            if widget.is_link and not is_multi_select:
                goto_action = menu.addAction("Go to Directory")
            if action := menu.exec(self.mapToGlobal(pos)):
                if action == remove_action:
                    items_to_remove = selected_items if is_multi_select else [item]
                    for sel_item in items_to_remove:
                        sel_widget = self.itemWidget(sel_item)
                        self.main_window.logic.remove_item(sel_widget.item_name, sel_widget.is_link)
                elif widget.is_link and action == goto_action:
                    self.main_window.logic.go_to_directory(widget.item_name, widget.is_link)

    def handle_double_click(self, item):
        if (widget := self.itemWidget(item)) and not widget.is_link:
            widget.start_editing()

    def show_context_menu(self, pos):
        if item := self.itemAt(pos):
            widget, selected_items = self.itemWidget(item), self.selectedItems()
            menu = QMenu(self)
            is_multi_select = len(selected_items) > 1 and item in selected_items
            remove_action = menu.addAction("Remove Selected" if is_multi_select else "Remove")
            if widget.is_link and not is_multi_select:
                goto_action = menu.addAction("Go to Directory")
            if action := menu.exec(self.mapToGlobal(pos)):
                if action == remove_action:
                    items_to_remove = selected_items if is_multi_select else [item]
                    for sel_item in items_to_remove:
                        sel_widget = self.itemWidget(sel_item)
                        self.main_window.logic.remove_item(sel_widget.item_name, sel_widget.is_link)
                elif widget.is_link and action == goto_action:
                    self.main_window.logic.go_to_directory(widget.item_name, widget.is_link)
                    
class FileDropArea(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAcceptDrops(True)
        self.setFixedSize(30, 30)
        self.setStyleSheet("QWidget { background-color: #e0e0e0; border: 1px dashed #808080; border-radius: 5px; } QWidget:hover { background-color: #c0c0c0; border: 1px solid #404040; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(QLabel("🔗", alignment=Qt.AlignCenter))
        self.setToolTip("Drop files here for live links")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if file_path := url.toLocalFile():
                    self.main_window.logic.process_file_drop(file_path, is_link=True)
            event.acceptProposedAction()

class OpacityControl(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedSize(20, 20)
        self.setStyleSheet("background-color: #d0d0d0; border: 1px solid #808080; border-radius: 3px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("👻", alignment=Qt.AlignCenter))
        self.setToolTip("Scroll to adjust opacity (15%–100%)")

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.main_window.setWindowOpacity(max(0.15, min(1.0, self.main_window.windowOpacity() + (0.05 if delta > 0 else -0.05))))
        self.main_window.logic.save_state()

class MainWindowLogic:
    def __init__(self, window):
        self.window, self.items, self.is_collapsed, self.previous_height, self.app = window, [], False, 400, QApplication.instance()

    def load_state(self):
        return json.load(open(STATE_FILE, "r")) if os.path.exists(STATE_FILE) else {"items": [], "opacity": DEFAULT_OPACITY, "width": 200, "height": 200}

    def save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump({"items": self.items, "opacity": self.window.windowOpacity(), "width": self.window.width(), "height": self.window.height() if not self.is_collapsed else self.previous_height}, f, indent=4)

    def add_item_to_list(self, name, is_link, link_path=None, checked=False):
        widget = IdeaItemWidget(name, is_link, link_path, main_window=self.window)
        widget.context_checkbox.setChecked(checked)
        list_item = QListWidgetItem(self.window.list_widget)
        list_item.setSizeHint(widget.sizeHint())
        self.window.list_widget.setItemWidget(list_item, widget)

    def process_file_drop(self, file_path, is_link):
        base_name, name = os.path.basename(file_path), os.path.splitext(os.path.basename(file_path))[0]
        if not any(item["name"] == name and item.get("is_link", False) == is_link for item in self.items):
            item_data = {"name": name, "is_link": is_link, **({"link_path": os.path.abspath(file_path)} if is_link else {"content": read_file_content(file_path)}), "checked": False}
            self.items.append(item_data)
            self.add_item_to_list(name, is_link, item_data.get("link_path"), False)
            self.save_state()

    def process_folder_drop(self, folder_path):
        clipboard_count = sum(1 for item in self.items if item["name"].startswith("📎 clipboard-")) + 1
        name, formatted_content = f"📎 clipboard-{clipboard_count}", []
        for root, _, files in os.walk(folder_path):
            relative_root = os.path.relpath(root, folder_path)
            if any(relative_root.startswith(blocked) for blocked in BLOCKED_DIRECTORIES):
                continue
            for file_name in files:
                if any(file_name.lower().endswith(ext) for ext in TEXT_EXTENSIONS):
                    file_path = os.path.join(root, file_name)
                    formatted_content.extend([f"📎 {os.path.relpath(file_path, folder_path)}", "```", read_file_content(file_path), "```"])
        if formatted_content:
            self.items.append({"name": name, "is_link": False, "content": "\n".join(formatted_content), "checked": False})
            self.add_item_to_list(name, False, None, False)
            self.save_state()

    def remove_item(self, name, is_link):
        if item_data := next((item for item in self.items if item["name"] == name and item.get("is_link", False) == is_link), None):
            self.items.remove(item_data)
            for i in range(self.window.list_widget.count()):
                if (widget := self.window.list_widget.itemWidget(self.window.list_widget.item(i))).item_name == name and widget.is_link == is_link:
                    self.window.list_widget.takeItem(i)
                    break
            self.save_state()

    def update_item_state(self, name, is_link, checked):
        if item_data := next((item for item in self.items if item["name"] == name and item.get("is_link", False) == is_link), None):
            item_data["checked"] = checked
            self.save_state()

    def update_item_name(self, old_name, is_link, new_name):
        if (item_data := next((item for item in self.items if item["name"] == old_name and item.get("is_link", False) == is_link), None)) and not any(item["name"] == new_name for item in self.items if item != item_data):
            item_data["name"] = new_name
            self.save_state()

    def go_to_directory(self, name, is_link):
        open_directory(next(item["link_path"] for item in self.items if item["name"] == name and item.get("is_link", False) == is_link))

    def clear_context(self):
        for i in range(self.window.list_widget.count()):
            widget = self.window.list_widget.itemWidget(self.window.list_widget.item(i))
            widget.context_checkbox.setChecked(False)
            self.update_item_state(widget.item_name, widget.is_link, False)

    def copy_context(self):
        formatted_text = [line for i in range(self.window.list_widget.count()) if (widget := self.window.list_widget.itemWidget(self.window.list_widget.item(i))).context_checkbox.isChecked() for line in [widget.link_path if widget.is_link else widget.item_name, "```", read_file_content(widget.link_path) if widget.is_link else next(item["content"] for item in self.items if item["name"] == widget.item_name and item.get("is_link", False) == widget.is_link), "```", ""]]
        if formatted_text:
            pyperclip.copy("\n".join(formatted_text))

    def add_clipboard_cold_link(self):
        if clipboard_text := pyperclip.paste().strip():
            clipboard_count = sum(1 for item in self.items if item["name"].startswith("📎 ")) + 1
            name = f"📎 clipboard-{clipboard_count}"
            if not any(item["name"] == name for item in self.items):
                self.items.append({"name": name, "is_link": False, "content": clipboard_text, "checked": False})
                self.add_item_to_list(name, False, None, False)
                self.save_state()

    def toggle_always_on_top(self):
        self.window.setWindowFlags(self.window.windowFlags() | Qt.WindowStaysOnTopHint if self.window.top_toggle.isChecked() else self.window.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.window.show()

    def toggle_collapse(self):
        self.window.list_widget.setVisible(not self.is_collapsed)
        self.window.collapse_button.setText("▼" if self.is_collapsed else "▲")
        if self.is_collapsed:
            self.window.setMinimumHeight(0)
            self.window.setMaximumHeight(16777215)
            self.window.resize(self.window.width(), self.previous_height)
        else:
            self.previous_height = self.window.height()
            self.window.setFixedHeight(40 + self.window.frameGeometry().height() - self.window.geometry().height())
        self.is_collapsed = not self.is_collapsed
        self.save_state()