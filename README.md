## 🚀 Overview
ContextYap is a tool for rapidly managing your AI's context.

## ✨ Main Features
- Drop files into the main list body for cold copies or onto the 🔗 icon for live links to the original file.

- Toggle items that will be sent to your clipboard when you press `C` by simply toggling the boxes on the left side of the file names.

- Press `CC` to clear your selection and toggle all boxes off.

- Click 📎 to paste clipboard content as a new list item (e.g., "clipboard-1"). Double-click the name to rename clipboard items.


## ✨ Extra Features
- Right-click to see a context menu with options to either "Delete" or "Go to Directory".

- Toggle 📌 to keep the window always on top of other windows.

- Scroll over 👻 to adjust transparency (15-100%).

- Toggle collapsed list state by clicking ▲▼.

```markdown
Requirements: Python 3.x, PySide6, pyperclip

## 🛠️ Setup (virtual environment)
   Clone or download this repository (git clone https://github.com/42Cup).
   cd ContextYap
   python -m venv svenv
   source svenv/bin/activate
   pip install PySide6 pyperclip
   python context_yap.py

## no virtual environment
   Clone or download this repository (git clone https://github.com/42Cup).
   cd ContextYap
   python pip install PySide6 pyperclip
   python context_yap.py

## 📋 Clipboard Paste Example

/path/to/file
'''
file content
'''