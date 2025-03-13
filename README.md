# Context Grabber

## Overview
Context Grabber is a lightweight, efficient desktop application designed to streamline the process of gathering and managing file content for AI context or other uses. Drag and drop files to link them live or store copies, select items to include in your context, and copy their contents to your clipboard with ease. This open-source tool is built for simplicity and functionality—perfect for developers, writers, or anyone needing quick file aggregation.

## Features
- **Drag and Drop Files**: Add multiple files at once by dragging them into the list (creates copies) or onto the link icon (creates live links to original files).
- **Context Selection**: Toggle items with checkboxes to include or exclude them from your context; drag to select multiple items or use shift-click for bulk selection.
- **Clipboard Copy**: Copy the contents of selected files to your clipboard, formatted with file paths and code blocks for easy pasting.
- **File Management**: Right-click to remove individual items or go to their directories; multi-select and remove several items at once.
- **Always On Top**: Toggle the window to stay on top of other applications for constant accessibility.
- **Persistent State**: Saves your file list and selections between sessions using a `state.json` file.

## Requirements
- Python 3.x
- PySide6 (Qt for Python)
- pyperclip

## Installation
1. Clone or download this repository to your local machine.
2. Install the required dependencies:
   ```bash
   pip install PySide6 pyperclip
   ```
3. Run the application:
   ```bash
   python context_grabber.py
   ```

## Usage
- **Adding Files**:
  - Drag files onto the main list to create local copies in an `ideas/` directory.
  - Drag files onto the 🔗 icon in the header to link them live from their original locations.
- **Selecting Context**:
  - Click the checkboxes on the left to toggle items on or off.
  - Drag across checkboxes to select multiple items quickly.
  - Click one item, then Shift+click another to select a range.
- **Managing Files**:
  - Right-click an item for "Remove" (deletes it) or "Go to Directory" (opens its folder).
  - Multi-select items (via Shift+click), then right-click for "Remove Selected" to delete them all at once.
- **Copying Context**:
  - Press the "C" button to copy the contents of all selected files to your clipboard, formatted as:
    ```
    /path/to/file
    '''
    file content here
    '''
    ```
  - Errors (e.g., file not found) are included in the output for transparency.
- **Clearing Context**:
  - Press the "CC" button to uncheck all items and reset your selection.
- **Staying On Top**:
  - Click the 📌 button to toggle the window’s "Always On Top" mode (orange when active, grey when off).

## Notes
- **File Storage**: Non-linked files are copied to an `ideas/` directory in the app’s working directory. Linked files reference their original paths.
- **State Persistence**: The app saves your file list and checkbox states to `state.json` on every change, loading them on startup.
- **Platform Support**: Works on Windows, macOS, and Linux, with native directory opening (`xdg-open`, `open`, or `os.startfile`).

## Contributing
Feel free to fork, tweak, and submit pull requests! This is a community-driven project—let’s make it better together.

## License
Free and open-source under the MIT License. Use it, share it, and enjoy!