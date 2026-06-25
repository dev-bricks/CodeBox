<img src="assets/banner.svg" width="100%" alt="CodeBox Banner">

# CodeBox - local PySide6 desktop code editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()
[![LSP Ready](https://img.shields.io/badge/LSP-ready-purple.svg)]()

[Deutsch](README_de.md) | English

CodeBox is a local-first desktop IDE for Windows developers who want a
lightweight PySide6 code editor with tabs, a project tree, an integrated
terminal, Git helpers, syntax highlighting, and Language Server Protocol
diagnostics.

## Start here

| Need | Start with |
| --- | --- |
| Run the editor from source | `pip install -r requirements.txt` and `python main.py` |
| Open a file directly | `python main.py --open path/to/file.py` |
| Build a local Windows executable | `build_exe.bat` |
| Add diagnostics or completion | Install a local language server such as `python-lsp-server[all]` |
| Understand the roadmap | [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) |

## Why CodeBox

- Local-first: edit files on your machine without cloud accounts or telemetry.
- PySide6 desktop stack: native Windows app behavior with a small Python codebase.
- Multi-language workflow: Python, JavaScript, TypeScript, C++, Rust, Go and Java.
- LSP-ready: diagnostics and completion can connect to installed language servers.
- Dev-bricks ecosystem: companion to PythonBox and DevCenter for small local tools.

## Screenshot

![CodeBox main window with project tree, editor tabs, output panel, and terminal](README/screenshots/main.png)

## Features

- Syntax highlighting for Python, JavaScript, TypeScript, C++, Rust, Go, and Java
- Integrated terminal with shell selection and command history
- Project file tree with filtering and context menus
- Multiple editor tabs, search, and go-to-line navigation
- Robust tab handling with drag-and-drop reordering and save-failure guards
- Theme system via `features/theme_manager.py`
- REST API and CLI foundation for later remote control
- LSP diagnostics and completion for installed language servers

## Installation

```bash
git clone https://github.com/dev-bricks/CodeBox
cd CodeBox
pip install -r requirements.txt
python main.py
```

You can also start the app on Windows by double-clicking `start.bat`.

### Requirements

- Python 3.10+
- PySide6 >= 6.5.0

### Optional language servers

- Python: `pip install "python-lsp-server[all]"` for completion and diagnostics
  (`pip install python-lsp-server` is enough for completion only)
- TypeScript: `npm install -g typescript-language-server`
- Rust: `rustup component add rust-analyzer`
- Go: `go install golang.org/x/tools/gopls@latest`
- C++: install `clangd` through LLVM

CodeBox prefers `pylsp` on `PATH`. If the script is not on `PATH`, it falls back
to the current Python interpreter with `python -m pylsp`. The UI availability
check uses the same fallback logic.

### Optional remote-editing dependency

The prepared SSH/SFTP layer uses `paramiko`, but it is not required for the
local editor startup:

```bash
pip install paramiko
```

## Local Windows build

```bat
build_exe.bat
```

The script uses PyInstaller and creates a local `CodeBox.exe` with
`CodeBox.ico`. The versioned `CodeBox.spec` bundles icon and theme files, while
temporary build data stays under `C:\_Local_DEV\codex_build\codebox`. Build
outputs in `build/`, `dist/`, and `releases/` remain local artifacts and are not
versioned.

`start.bat` first looks for `dist\CodeBox.exe`, then for an existing release EXE,
and finally falls back to `python main.py`.

## Project structure

```text
main.py            Application entry point
core/              Editor core, tabs, output panel, highlighter
features/          Terminal, project tree, LSP, Git, themes, remote editing
languages/         Language profiles and LSP configuration
ui/                MainWindow and UI composition
config/            Configuration files
themes/            QSS themes
README/screenshots Screenshot assets for the project page
```

## Search and disambiguation

CodeBox is best described as a local PySide6 code editor, Windows desktop IDE,
offline code editor, LSP-enabled Python editor, and lightweight multi-language
developer tool. The repository name collides with older projects called
`codebox`, so searches are most precise with `dev-bricks CodeBox`,
`CodeBox PySide6`, `CodeBox LSP editor`, `CodeBox local desktop IDE`, or
`PySide6 code editor with LSP diagnostics`.

## Status

Current status: `DEV`, version `0.1.0`.

Already usable:

- Multi-language editor
- Project tree and terminal in the main window
- Consistent window titles via `version.py`
- Light/dark theme switching through the central theme manager
- Save, close, and run flows that keep tabs open if a filesystem error prevents saving

Open for the next larger expansion:

- Runtime test with an installed LSP server
- Linter/problems panel
- Plugin system for additional languages
- Remote editing over SSH/SFTP

## Privacy

CodeBox works locally on files that the user opens. The base editor does not
require credentials and does not contact external services unless you start a
local language server, external build/run tools, or optional remote-editing
features yourself.

Optional remote connections may use SSH passwords or key paths at runtime. Such
data does not belong in the repository and should only live in local ignored
configuration files or the system keyring.

Local working files such as `AUFGABEN.txt`, test locks, `.env` files,
credentials, SSH keys, logs, databases, and build artifacts are excluded through
`.gitignore`.

## License

[MIT License](LICENSE)

## Liability

This project is an unpaid open-source donation. Liability is limited to intent
and gross negligence (Section 521 German Civil Code). Use at your own risk. No
warranty, maintenance guarantee, or fitness-for-purpose is assumed.
