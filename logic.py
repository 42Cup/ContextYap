#!/usr/bin/env python3
import os, json, subprocess, sys, pyperclip

STATE_FILE, DEFAULT_OPACITY = "state.json", 0.85
TEXT_EXTENSIONS, BLOCKED_DIRECTORIES = {'.js', '.md'}, ['src/locale']

# Default values for directory tree settings
# These may be updated at runtime from contextyap.py
EXCLUDED_DIRS = ["node_modules", ".git", "dist", "build"]
MAX_TREE_DEPTH = 3

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
        if is_dir: 
            return self.process_folder_drop(path, is_link)
        else: 
            return self.process_file_drop(path, is_link)

    def process_file_drop(self, file_path, is_link):
        file_name = os.path.basename(file_path)  # Keep full filename with extension
        dir_name = os.path.basename(os.path.dirname(file_path))
        name = f"{file_name}-{dir_name}"
        if not self.find_item(name, is_link):
            content = self.read_file(file_path) if not is_link else None
            item_data = {"name": name, "is_link": is_link, "link_path": os.path.abspath(file_path) if is_link else None, "checked": False}
            if content: item_data["content"] = content
            self.items.append(item_data)
            self.save_state()
            return item_data
        return None

    def process_folder_drop(self, folder_path, is_link=False):
        folder_name = os.path.basename(folder_path)
        parent_dir = os.path.basename(os.path.dirname(folder_path))
        name = self.generate_unique_name(f"📎 {folder_name}-{parent_dir}-") if not is_link else f"{folder_name}-{parent_dir}"
        
        if is_link:
            # Only store the path for live link
            item_data = {"name": name, "is_link": True, "link_path": os.path.abspath(folder_path), "checked": False, "is_dir": True}
            self.items.append(item_data)
            self.save_state()
            return item_data
        else:
            # For cold links, generate and store the directory structure visualization
            dir_structure = self.generate_directory_structure(folder_path)
            
            if dir_structure:
                item_data = {"name": name, "is_link": False, "content": dir_structure, "checked": False, "is_dir": True}
                self.items.append(item_data)
                self.save_state()
                return item_data
        return None
    
    def generate_directory_structure(self, folder_path):
        """Generate a text representation of the directory structure."""
        folder_name = os.path.basename(folder_path)
        result = [f"{folder_name}/"]
        
        # Process the directory tree with depth tracking
        self._process_directory_tree(folder_path, result, "", 0, False)
        
        return "\n".join(result)
    
    def _process_directory_tree(self, path, result, prefix, depth, is_last_at_level):
        """Recursively process a directory tree with proper indentation"""
        # Skip if we've exceeded the maximum depth
        if depth > MAX_TREE_DEPTH:
            return
            
        # Get directories and files in the current path
        try:
            entries = sorted(os.listdir(path))
        except (PermissionError, FileNotFoundError):
            # Handle permission errors or non-existent directories gracefully
            return
            
        # Separate directories and files
        dirs = []
        files = []
        
        for entry in entries:
            entry_path = os.path.join(path, entry)
            if os.path.isdir(entry_path):
                dirs.append(entry)
            elif os.path.isfile(entry_path):
                files.append(entry)
        
        # Process all entries
        all_entries = []
        
        # Add directories first (with trailing slash)
        for d in dirs:
            all_entries.append((d, True))
            
        # Add files
        for f in files:
            all_entries.append((f, False))
            
        # Process each entry
        for i, (entry, is_dir) in enumerate(all_entries):
            is_last = (i == len(all_entries) - 1)
            
            # Determine the correct prefix for this item
            if depth > 0:
                entry_prefix = prefix + ("└── " if is_last else "├── ")
            else:
                entry_prefix = prefix
                
            # Add the entry to the result
            if is_dir:
                result.append(f"{entry_prefix}{entry}/")
                
                # Skip expanding excluded directories
                if entry in EXCLUDED_DIRS:
                    continue
                
                # Skip if we've reached max depth
                if depth >= MAX_TREE_DEPTH:
                    continue
                    
                # Determine the next level's prefix based on whether this is the last item
                next_prefix = prefix + ("    " if is_last else "│   ")
                
                # Recursively process subdirectory
                self._process_directory_tree(
                    os.path.join(path, entry),
                    result,
                    next_prefix,
                    depth + 1,
                    is_last
                )
            else:
                result.append(f"{entry_prefix}{entry}")

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
        item = next((item for item in self.items if item["name"] == name and item.get("is_link", False) == is_link), None)
        if item and (path := item.get("link_path")):
            if os.path.exists(path):
                opener = {"win32": os.startfile, "darwin": lambda p: subprocess.Popen(["open", p]), "linux": lambda p: subprocess.Popen(["xdg-open", p])}.get(sys.platform, lambda x: None)
                # If it's a directory link, open the directory directly, otherwise open the parent directory
                target_path = path if item.get("is_dir", False) else os.path.dirname(path)
                opener(target_path)
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
                if item.get("is_link", False) and item.get("is_dir", False):
                    # For live directory links, generate the current structure
                    content = self.generate_directory_structure(item["link_path"])
                elif item.get("is_link", False):
                    # For regular file links
                    content = self.read_file(item["link_path"])
                else:
                    # For cold links (both files and directories)
                    content = item.get("content", "[No content available]")
                
                context_items.append({
                    "name": item["name"],
                    "is_link": item.get("is_link", False),
                    "path": item.get("link_path"),
                    "content": content,
                    "is_dir": item.get("is_dir", False)
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
            name = self.generate_unique_name("📎 clipboard-")
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