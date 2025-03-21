#!/usr/bin/env python3
import os, json, subprocess, sys, pyperclip

STATE_FILE, DEFAULT_OPACITY = "state.json", 0.85
TEXT_EXTENSIONS, BLOCKED_DIRECTORIES = {'.js', '.md'}, ['src/locale']

class AppLogic:
    def __init__(self):
        self.state = self.load_state()
        self.items = self.state.get("items", [])
        self.opacity = self.state.get("opacity", DEFAULT_OPACITY)
        self.width = self.state.get("width", 200)
        self.height = self.state.get("height", 400)
        self.is_collapsed = False
        self.previous_height = self.height

    def process_drop(self, path, is_dir, is_link=False):
        if is_dir: return self.process_folder_drop(path)
        else: return self.process_file_drop(path, is_link)

    def process_file_drop(self, file_path, is_link):
        name = os.path.splitext(os.path.basename(file_path))[0]
        if not self.find_item(name, is_link):
            content = self.read_file(file_path) if not is_link else None
            item_data = {"name": name, "is_link": is_link, "link_path": os.path.abspath(file_path) if is_link else None, "checked": False}
            if content: item_data["content"] = content
            self.items.append(item_data)
            self.save_state()
            return item_data
        return None

    def process_folder_drop(self, folder_path):
        name = self.generate_unique_name("📎 clipboard-")
        formatted_content = []
        for root, _, files in os.walk(folder_path):
            if any(os.path.relpath(root, folder_path).startswith(blocked) for blocked in BLOCKED_DIRECTORIES): continue
            for file_name in files:
                if any(file_name.lower().endswith(ext) for ext in TEXT_EXTENSIONS):
                    file_path = os.path.join(root, file_name)
                    if content := self.read_file(file_path):
                        formatted_content.extend([f"📎 {os.path.relpath(file_path, folder_path)}", "```", content, "```"])
        if formatted_content:
            item_data = {"name": name, "is_link": False, "content": "\n".join(formatted_content), "checked": False}
            self.items.append(item_data)
            self.save_state()
            return item_data
        return None

    def read_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return f.read()
        except Exception as e: return f"[Error reading file: {e}]"

    def generate_unique_name(self, prefix):
        count = sum(1 for item in self.items if item["name"].startswith(prefix)) + 1
        name = f"{prefix}{count}"
        while any(item["name"] == name for item in self.items):
            count += 1
            name = f"{prefix}{count}"
        return name

    def remove_item(self, name, is_link):
        if item_data := self.find_item(name, is_link):
            self.items.remove(item_data)
            self.save_state()
            return True
        return False

    def update_item_state(self, name, is_link, checked):
        if item_data := self.find_item(name, is_link):
            print(f"Found item to update: {item_data['name']}")
            item_data["checked"] = checked
            self.save_state()
            return True
        print(f"Item not found for update: {name}, is_link: {is_link}")
        return False

    def update_item_name(self, old_name, is_link, new_name):
        if (item_data := self.find_item(old_name, is_link)) and not any(item["name"] == new_name for item in self.items if item != item_data):
            item_data["name"] = new_name
            self.save_state()
            return True
        return False

    def find_item(self, name, is_link):
        return next((item for item in self.items if item["name"] == name and item.get("is_link", False) == is_link), None)

    def go_to_directory(self, name, is_link):
        if path := next((item["link_path"] for item in self.items if item["name"] == name and item.get("is_link", False) == is_link), None):
            if os.path.exists(path):
                opener = {"win32": os.startfile, "darwin": lambda p: subprocess.Popen(["open", p]), "linux": lambda p: subprocess.Popen(["xdg-open", p])}.get(sys.platform, lambda x: None)
                opener(os.path.dirname(path))
                return True
        return False

    def clear_context(self):
        for item in self.items:
            item["checked"] = False
        self.save_state()

    def get_context_items(self):
        context_items = []
        for item in self.items:
            if item.get("checked", False):
                content = self.read_file(item["link_path"]) if item.get("is_link", False) else item.get("content", "[No content available]")
                context_items.append({
                    "name": item["name"],
                    "is_link": item.get("is_link", False),
                    "path": item.get("link_path"),
                    "content": content
                })
        return context_items

    def copy_context(self):
        formatted_text = []
        context_items = self.get_context_items()
        print(f"Logic copy_context: found {len(context_items)} checked items")
        
        for item in context_items:
            name_or_path = item["path"] if item["is_link"] else item["name"]
            print(f"Processing item: {name_or_path}")
            formatted_text.append(f"{name_or_path}")
            formatted_text.append("```")
            formatted_text.append(item["content"])
            formatted_text.append("```")
            formatted_text.append("")
            
        print(f"Final formatted text has {len(formatted_text)} lines")
        if formatted_text: 
            text = "\n".join(formatted_text)
            print(f"Copying text of length {len(text)} to clipboard")
            try:
                pyperclip.copy(text)
                print("Successfully copied to clipboard:")
                print(text)
                return True
            except Exception as e:
                print(f"Error copying to clipboard: {e}")
                return False
        return False

    def add_clipboard_content(self):
        if clipboard_text := pyperclip.paste().strip():
            name = self.generate_unique_name("📎 ")
            item_data = {"name": name, "is_link": False, "content": clipboard_text, "checked": False}
            self.items.append(item_data)
            self.save_state()
            return item_data
        return None

    def update_window_state(self, opacity=None, width=None, height=None, is_collapsed=None, previous_height=None):
        if opacity is not None: self.opacity = opacity
        if width is not None: self.width = width
        if height is not None: self.height = height
        if is_collapsed is not None: self.is_collapsed = is_collapsed
        if previous_height is not None: self.previous_height = previous_height
        self.save_state()

    def load_state(self):
        return json.load(open(STATE_FILE, "r")) if os.path.exists(STATE_FILE) else {"items": [], "opacity": DEFAULT_OPACITY, "width": 200, "height": 200}

    def save_state(self):
        state_data = {
            "items": self.items,
            "opacity": self.opacity,
            "width": self.width,
            "height": self.height if not self.is_collapsed else self.previous_height
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state_data, f, indent=4)