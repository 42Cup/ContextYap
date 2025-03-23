#!/usr/bin/env python3
import os, sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QListWidget, QListWidgetItem, QHBoxLayout, 
    QVBoxLayout, QWidget, QCheckBox, QToolButton, QLabel, QMenu, QPushButton, QLineEdit)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QIcon

from logic import AppLogic

def create_tool_button(text, max_width, base_style, checked_style="", parent=None):
    button = QToolButton(parent)
    button.setText(text)
    button.setMaximumWidth(max_width)
    button.setStyleSheet(base_style + checked_style)
    if "checked" in checked_style: button.setCheckable(True)
    return button

class DragSelectableCheckBox(QCheckBox):
    _drag_active, _target_state = False, None

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        app = QApplication.instance()
        if app: app.installEventFilter(self)
        self.setStyleSheet(IdeaItemWidget.CHECKBOX_STYLE)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease:
            DragSelectableCheckBox._drag_active = False
            DragSelectableCheckBox._target_state = None
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            current_time = event.timestamp()
            if hasattr(self, '_last_click_time') and (current_time - self._last_click_time < 300):
                self.main_window.clear_context()
            else:
                DragSelectableCheckBox._drag_active = True
                DragSelectableCheckBox._target_state = not self.isChecked()
                self.setChecked(DragSelectableCheckBox._target_state)
                # Find the parent IdeaItemWidget and update the state
                parent_widget = self.parent()
                if isinstance(parent_widget, IdeaItemWidget):
                    print(f"Checkbox clicked: {parent_widget.item_name}, new state: {DragSelectableCheckBox._target_state}")
                    self.main_window.update_item_state(parent_widget.item_name, parent_widget.is_link, DragSelectableCheckBox._target_state)
            self._last_click_time = current_time
            event.accept()
            return
        super().mousePressEvent(event)

class IdeaItemWidget(QWidget):
    CHECKBOX_STYLE = "QCheckBox::indicator { background-color: grey; border: 1px solid black; width: 15px; height: 15px; } QCheckBox::indicator:checked { background-color: lightblue; }"

    def __init__(self, item_name, is_link=False, link_path=None, main_window=None, is_dir=False, parent=None):
        super().__init__(parent)
        self.item_name = item_name
        self.is_link = is_link
        self.link_path = link_path
        self.main_window = main_window
        self.is_dir = is_dir
        self.is_editing = False
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.context_checkbox = DragSelectableCheckBox(self.main_window)
        self.layout.addWidget(self.context_checkbox)
        
        if is_link:
            self.link_indicator = QLabel()
            self.link_indicator.setFixedSize(12, 12)
            self.link_indicator.setStyleSheet("background-color: #00aa00; border-radius: 6px;")
            tooltip = f"Live {'Directory' if is_dir else 'File'} Link: {link_path}"
            self.link_indicator.setToolTip(tooltip)
            self.layout.addWidget(self.link_indicator)
        
        # Add directory icon if it's a directory item
        if is_dir:
            dir_icon = QLabel("📁")
            dir_icon.setFixedSize(16, 16)
            dir_icon.setToolTip("Directory Structure")
            self.layout.addWidget(dir_icon)
            
        self.name_label, self.name_edit = QLabel(item_name), QLineEdit(item_name)
        self.name_edit.hide()
        self.name_edit.returnPressed.connect(self.finish_editing)
        self.name_edit.editingFinished.connect(self.cancel_editing)
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.name_edit)
        self.layout.addStretch()

    def start_editing(self):
        self.is_editing = True
        self.name_label.hide()
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
                if not self.is_link: new_name = f"📎 {new_name}"
                self.item_name = new_name
                self.name_label.setText(new_name)
                self.main_window.update_item_name(old_name, self.is_link, new_name)
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

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path: self.main_window.process_drop(path, os.path.isdir(path))
            event.acceptProposedAction()
        else: super().dropEvent(event)

    def mouseMoveEvent(self, event):
        if DragSelectableCheckBox._drag_active and DragSelectableCheckBox._target_state is not None:
            item = self.itemAt(event.pos())
            if item:
                widget = self.itemWidget(item)
                if widget and isinstance(widget, IdeaItemWidget):
                    checkbox = widget.context_checkbox
                    if checkbox.isChecked() != DragSelectableCheckBox._target_state:
                        checkbox.setChecked(DragSelectableCheckBox._target_state)
                        self.main_window.update_item_state(widget.item_name, widget.is_link, DragSelectableCheckBox._target_state)
                    event.accept()
                    return
        super().mouseMoveEvent(event)

    def handle_double_click(self, item):
        widget = self.itemWidget(item)
        if widget and not widget.is_link: widget.start_editing()

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item:
            widget, selected_items = self.itemWidget(item), self.selectedItems()
            menu = QMenu(self)
            if len(selected_items) > 1 and item in selected_items:
                remove_action = menu.addAction("Remove Selected")
                if menu.exec(self.mapToGlobal(pos)) == remove_action:
                    for sel_item in selected_items:
                        sel_widget = self.itemWidget(sel_item)
                        self.main_window.remove_item(sel_widget.item_name, sel_widget.is_link)
            else:
                remove_action = menu.addAction("Remove")
                goto_action = menu.addAction("Go to Directory") if widget.is_link else None
                action = menu.exec(self.mapToGlobal(pos))
                if action == remove_action: self.main_window.remove_item(widget.item_name, widget.is_link)
                elif action == goto_action: self.main_window.go_to_directory(widget.item_name, widget.is_link)

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
        self.setToolTip("Drop files or directories here for live links")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if (file_path := url.toLocalFile()): 
                    is_dir = os.path.isdir(file_path)
                    self.main_window.process_drop(file_path, is_dir, True)
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
        opacity = self.main_window.windowOpacity()
        new_opacity = max(0.15, min(1.0, opacity + (0.05 if delta > 0 else -0.05)))
        self.main_window.setWindowOpacity(new_opacity)
        self.main_window.app_logic.update_window_state(opacity=new_opacity)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_logic = AppLogic()
        
        self.setWindowTitle("ContextYap")
        self.setWindowIcon(QIcon("icon.jpg"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.setWindowOpacity(self.app_logic.opacity)
        self.resize(self.app_logic.width, self.app_logic.height)
        
        base_style = "QToolButton { background: #808080; color: white; border: 1px solid #808080; padding: 5px; }"
        header_layout = QHBoxLayout()
        self.top_toggle = create_tool_button("📌", 30, base_style, " QToolButton:checked { background: #ffaa00; color: white; }", self)
        self.top_toggle.setChecked(True)
        self.top_toggle.clicked.connect(self.toggle_always_on_top)
        header_layout.addWidget(self.top_toggle)
        
        self.cc_button = create_tool_button("CC", 30, base_style, parent=self)
        self.cc_button.clicked.connect(self.clear_context)
        self.c_button = create_tool_button("C", 20, base_style, parent=self)
        self.c_button.clicked.connect(self.copy_context)
        self.collapse_button = create_tool_button("▲", 20, base_style, parent=self)
        self.collapse_button.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.cc_button)
        header_layout.addWidget(self.c_button)
        header_layout.addWidget(self.collapse_button)
        
        self.opacity_control = OpacityControl(self)
        header_layout.addWidget(self.opacity_control)
        
        self.clipboard_button = QPushButton("📎", self)
        self.clipboard_button.setFixedWidth(20)
        self.clipboard_button.setStyleSheet("QPushButton { background-color: #4d4d4d; color: white; border: 1px solid #808080; padding: 5px; }")
        self.clipboard_button.clicked.connect(self.add_clipboard_cold_link)
        header_layout.addWidget(self.clipboard_button)
        
        header_layout.addStretch()
        self.file_drop_area = FileDropArea(self)
        header_layout.addWidget(self.file_drop_area)
        
        self.list_widget = DroppableListWidget(self)
        self.is_collapsed = False
        self.previous_height = self.app_logic.previous_height
        for item in self.app_logic.items: self.add_item_to_list(**item)
        
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.is_collapsed:
            self.app_logic.update_window_state(width=self.width(), height=self.height())

    def process_drop(self, path, is_dir, is_link=False):
        item_data = self.app_logic.process_drop(path, is_dir, is_link)
        if item_data: self.add_item_to_list(**item_data)

    def add_item_to_list(self, name, is_link=False, link_path=None, checked=False, is_dir=False, **kwargs):
        widget = IdeaItemWidget(name, is_link, link_path, self, is_dir)
        widget.context_checkbox.setChecked(checked)
        item = QListWidgetItem(self.list_widget)
        item.setSizeHint(widget.sizeHint())
        self.list_widget.setItemWidget(item, widget)

    def remove_item(self, name, is_link):
        if self.app_logic.remove_item(name, is_link):
            for i in range(self.list_widget.count()):
                widget = self.list_widget.itemWidget(self.list_widget.item(i))
                if widget.item_name == name and widget.is_link == is_link:
                    self.list_widget.takeItem(i)
                    break

    def update_item_state(self, name, is_link, checked):
        print(f"Updating item state: {name}, is_link: {is_link}, checked: {checked}")
        self.app_logic.update_item_state(name, is_link, checked)

    def update_item_name(self, old_name, is_link, new_name):
        self.app_logic.update_item_name(old_name, is_link, new_name)

    def go_to_directory(self, name, is_link):
        self.app_logic.go_to_directory(name, is_link)

    def clear_context(self):
        self.app_logic.clear_context()
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            widget.context_checkbox.setChecked(False)

    def copy_context(self):
        print("Copy context button clicked")
        context_items = self.app_logic.get_context_items()
        print(f"Context items count: {len(context_items)}")
        for item in context_items:
            print(f"Item: {item['name']}, is_link: {item['is_link']}")
        result = self.app_logic.copy_context()
        print(f"Copy result: {result}")


    def add_clipboard_cold_link(self):
        if item_data := self.app_logic.add_clipboard_content():
            self.add_item_to_list(**item_data)

    def toggle_always_on_top(self):
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowStaysOnTopHint if not self.top_toggle.isChecked() else self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self.list_widget.setVisible(not self.is_collapsed)
        self.collapse_button.setText("▼" if self.is_collapsed else "▲")
        
        if self.is_collapsed:
            self.previous_height = self.height()
            self.setFixedHeight(40 + self.frameGeometry().height() - self.geometry().height())
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.resize(self.width(), self.previous_height)
            
        self.app_logic.update_window_state(
            is_collapsed=self.is_collapsed,
            previous_height=self.previous_height
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()