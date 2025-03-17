# ContextYap

## 🚀 Overview
**ContextYap** is a sleek, open-source desktop tool for managing file content effortlessly. Drag and drop files to link or copy them, select what you need with a click, and copy their contents to your clipboard—perfect for AI context, coding, or quick aggregation. Built with simplicity and power in mind.

## ✨ Main Features
- **Drag & Drop Simplicity**: Drop files into the list for copies or onto the 🔗 icon for live links to originals.  
- **Smart Selection**: Toggle items with checkboxes—drag to select multiple or Shift+click for bulk control.  
- **Clipboard Magic**: Hit "C" to copy selected file contents, neatly formatted with paths and code blocks.  
- **File Control**: Right-click to remove items or jump to their directories; multi-select to batch-delete.  
- **Always Visible**: Toggle 📌 to keep the window on top; adjust opacity (15%–100%) with a scroll.  
- **Collapse & Save**: Collapse to a slim header with ▲▼; state auto-saves to `state.json`.  

## 📋 Usage
- **Add Files**: Drag to the list (copies) or 🔗 (live links).  
- **Select**: Check items, drag across checkboxes, or Shift+click.  
- **Copy**: Press "C" for formatted output:  
  ```
  /path/to/file
  ```
  ```
  file content
  ```
- **Manage**: Right-click for "Remove" or "Go to Directory"; multi-select for "Remove Selected".  
- **Clear**: "CC" unchecks all.  
- **Pin**: 📌 toggles always-on-top (orange = on).  
- **Opacity**: Scroll over 👻 to adjust transparency.  

## 💡 Notes
- **Storage**: Copies go to `ideas/`; links reference originals.  
- **Persistence**: File list, selections, and window settings save to `state.json`.  
- **Cross-Platform**: Runs on Windows, macOS, and Linux with native folder support.  

## 🛠️ Setup
1. Clone or download this repo.  
2. Install dependencies:  
   ```bash
   pip install PySide6 pyperclip
   ```  
3. Launch:  
   ```bash
   python context_yap.py
   ```  

**Requirements**: Python 3.x, PySide6, pyperclip.  

## 🤝 Contributing
Fork it, tweak it, PR it—let’s build something awesome together!  

## 📜 License
MIT—free to use, share, and enjoy!