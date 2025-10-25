---
title: Keyboard Shortcuts
description: Speed up your workflow with keyboard shortcuts in the Bifrost interface
---

Bifrost provides keyboard shortcuts to help you navigate and work more efficiently. All shortcuts work across Windows, Linux, and macOS (using Ctrl on Windows/Linux and Cmd on macOS).

## Quick Access (Cmd+K)

The Quick Access command palette provides fast search and navigation to forms, workflows, and scripts.

**Shortcut**: `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux)

### Features

- **Search forms**: Find and execute forms by name or description
- **Search workflows**: Navigate to workflow execution pages
- **Search scripts**: Find Python files and open them in the Code Editor
- **Fuzzy search**: Matches partial text in names and descriptions
- **Content search**: Searches inside Python files for code snippets

### How to Use

1. Press `Cmd+K` (or `Ctrl+K`) from anywhere in Bifrost
2. Type to search across forms, workflows, and scripts
3. Use arrow keys (`↑` `↓`) to navigate results
4. Press `Enter` to select and navigate
5. Press `Esc` to close

### Search Results

The Quick Access palette shows results grouped by type:

- **Forms** - Navigate to form execution page
- **Workflows** - Navigate to workflow execution page
- **Scripts** - Open Python file in Code Editor with Run panel

Each result displays:
- Name of the form/workflow/script
- Type badge (form, workflow, or script)
- Description or matched code snippet (for scripts)

### Examples

**Find a form**:
```
Cmd+K → type "create user" → Enter
```
Opens the "Create User" form execution page.

**Find a workflow**:
```
Cmd+K → type "sync" → Enter
```
Navigates to the sync workflow execution page.

**Find and edit a script**:
```
Cmd+K → type "helpers.py" → Enter
```
Opens `helpers.py` in the Code Editor.

**Search code content**:
```
Cmd+K → type "get_oauth_connection" → Enter
```
Finds scripts containing `get_oauth_connection` and shows matching lines.

## Code Editor Shortcuts

### Save File (Cmd+S)

Save the currently open file in the Code Editor.

**Shortcut**: `Cmd+S` (Mac) or `Ctrl+S` (Windows/Linux)

The save shortcut:
- Saves the active file in the editor
- Works with all file types (Python, JSON, YAML, etc.)
- Shows a success notification on save
- Clears the "unsaved changes" indicator
- Updates the file on the server immediately

**Usage**:
1. Make changes to a file in the Code Editor
2. Press `Cmd+S` (or `Ctrl+S`) to save
3. File is saved and changes are persisted

### Auto-save

The Code Editor also includes auto-save functionality:
- Automatically saves after 2 seconds of inactivity
- Saves when switching tabs or closing the editor
- Can be triggered manually with `Cmd+S`

## Navigation Shortcuts

### Quick Access Navigation

When the Quick Access palette is open:

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate through search results |
| `Enter` | Select highlighted result |
| `Esc` | Close Quick Access palette |

Results automatically scroll into view as you navigate.

## Tips

**Quick form execution**: Press `Cmd+K`, type the form name, press `Enter` - you can execute a form in seconds.

**Fast code navigation**: Use `Cmd+K` to search for code across all your Python files without manually browsing directories.

**Keyboard-only workflow**: You can search, navigate, and execute workflows entirely with the keyboard using Quick Access.

**Search by description**: Can't remember the exact name? Search by description text - Quick Access searches both names and descriptions.

**Script content search**: Quick Access searches inside `.py` files, showing you the matching line of code and line number.

## Browser Conflicts

Some keyboard shortcuts may conflict with browser shortcuts:

- **Cmd+K in Chrome/Edge**: Opens browser search bar
  - Bifrost's Quick Access overrides this within the app
- **Cmd+S in browsers**: Opens save dialog
  - Bifrost's save shortcut overrides this in the Code Editor

If shortcuts don't work, ensure you're clicking inside the Bifrost app first to give it focus.

## See Also

- [Code Editor Guide](/guides/local-dev/debugging/) - Using the Code Editor for development
- [Forms Guide](/guides/forms/creating-forms/) - Creating and executing forms
- [Workflows Guide](/guides/workflows/writing-workflows/) - Writing and running workflows
