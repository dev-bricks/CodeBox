<img src="assets/banner.svg" width="100%" alt="CodeBox Banner">

# CodeBox - Local PySide6 Desktop Code Editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![CI](https://github.com/dev-bricks/CodeBox/actions/workflows/ci.yml/badge.svg)](https://github.com/dev-bricks/CodeBox/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-164%20passed%20%7C%20100%25-brightgreen.svg)]()
[![Privacy: Zero-Egress](https://img.shields.io/badge/privacy-100%25%20local--first%20%7C%20zero--egress-success.svg)](SECURITY.md)
[![Security Policy](https://img.shields.io/badge/security-bilingual%20policy-blue.svg)](SECURITY.md)
[![Ecosystem: dev-bricks](https://img.shields.io/badge/ecosystem-dev--bricks-blue.svg)](https://github.com/dev-bricks)
[![Part of: open-bricks](https://img.shields.io/badge/part%20of-open--bricks-blue.svg)](https://github.com/open-bricks)
[![LSP Ready](https://img.shields.io/badge/LSP-ready-purple.svg)]()
[![Version: 0.1.2](https://img.shields.io/badge/version-0.1.2-green.svg)](CHANGELOG.md)
[![llms.txt](https://img.shields.io/badge/llms.txt-available-green.svg)](llms.txt)

[Deutsch](README_de.md) | English

CodeBox is a local-first desktop IDE for Windows, Linux, and macOS developers who want a lightweight PySide6 code editor with multi-tab workspace, project tree, integrated terminal, Git status porcelain indicators, syntax highlighting, Language Server Protocol (LSP) diagnostics, and an extensible JSON/Python language plugin architecture.

> [!NOTE]
> For AI agents and automated discovery, see [llms.txt](llms.txt) for machine-readable context, architecture summaries, and navigation pointers.

---

## Quick Navigation

- [Start Here](#start-here)
- [System Architecture](#system-architecture)
- [End-to-End Workflow Lifecycle](#end-to-end-workflow-lifecycle)
- [Key Capabilities & Runtime Invariants](#key-capabilities--runtime-invariants)
- [Visual Showcase](#visual-showcase)
- [Features](#features)
- [Installation & Quickstart](#installation--quickstart)
- [Language Server Protocol (LSP) Setup](#language-server-protocol-lsp-setup)
- [Declarative Plugin System](#declarative-plugin-system)
- [Local Windows Build](#local-windows-build)
- [Project Structure](#project-structure)
- [Sibling Ecosystem](#sibling-ecosystem)
- [Search & Disambiguation](#search--disambiguation)
- [Security & Privacy](#security--privacy)
- [License & Liability](#license--liability)

---

## Start Here

| Need | Start with |
| --- | --- |
| Run the editor from source | `pip install -r requirements.txt` and `python main.py` |
| Open a specific file directly | `python main.py --open path/to/file.py` |
| Manage plugins & languages | `Ctrl+Shift+P` or menu *Edit -> Plugins & Languages...* |
| View keyboard shortcuts reference | `F1` or menu *Help -> Keyboard Shortcuts* |
| Build standalone Windows executable | `build_exe.bat` |
| Add diagnostics or completion | Install a local language server such as `python-lsp-server[all]` |
| Explore the development plan | [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) |
| Read security guidelines | [SECURITY.md](SECURITY.md) |

---

## System Architecture

```mermaid
flowchart TD
    subgraph UI ["Desktop UI Layer (PySide6)"]
        MW["MainWindow (ui/main_window.py)"]
        TB["ToolBar & Action Dispatcher"]
        ST["StatusBar & Position/Encoding/Language"]
        MW --> TB
        MW --> ST
    end

    subgraph Core ["Editor Core & Tab Management"]
        Tabs["TabWidget (core/tabs.py)"]
        Ed["CodeEditor & UniversalHighlighter (core/highlighter.py)"]
        MM["Minimap Widget (core/minimap.py)"]
        BM["BracketMatcher (core/bracket_matcher.py)"]
        Tabs --> Ed
        Ed --> MM
        Ed --> BM
    end

    subgraph Workspace ["Workspace & Project Tree"]
        PT["ProjectTree & FilterProxy (features/project_tree.py)"]
        Git["Git Porcelain Status Resolver (features/git_status.py)"]
        PT --> Git
    end

    subgraph Diagnostics ["Language Server & Diagnostics Engine"]
        LSPMgr["LSPManager & Client Thread (features/lsp_manager.py)"]
        Linter["Background Linter (Ruff/flake8/ESLint) (features/linter.py)"]
        Prob["ProblemsPanel (ui/problems_panel.py)"]
        LSPMgr --> Prob
        Linter --> Prob
    end

    subgraph Runtime ["Execution & Extensibility"]
        Term["Integrated Terminal QProcess (features/terminal.py)"]
        Out["OutputPanel Process Runner (core/output.py)"]
        PluginMgr["PluginManager (features/plugin_manager.py)"]
        Decl["Declarative Providers (languages/declarative.py)"]
        Theme["ThemeManager (features/theme_manager.py)"]
        PluginMgr --> Decl
    end

    MW --> Tabs
    MW --> PT
    MW --> Diagnostics
    MW --> Term
    MW --> Out
    MW --> PluginMgr
    MW --> Theme
```

---

## End-to-End Workflow Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer
    participant UI as MainWindow
    participant Ed as CodeEditor (Tabs)
    participant Linter as Background Linter
    participant LSP as LSP Client Thread
    participant Prob as ProblemsPanel
    participant Term as Terminal / Runner

    Dev->>UI: Launch CodeBox & Open File
    UI->>Ed: Load Buffer & Attach UniversalHighlighter
    Ed-->>Dev: Render Syntax Highlighting & Line Numbers

    Dev->>Ed: Edit Code & Save (Ctrl+S)
    Ed->>Linter: Dispatch non-blocking lint trigger
    Ed->>LSP: Notify textDocument/didSave

    par Background Diagnostics
        Linter->>Linter: Execute Ruff / flake8 / ESLint (subprocess)
        Linter-->>Prob: Update Linter Diagnostics
    and Language Server Analysis
        LSP->>LSP: Query Language Server (pylsp / clangd / rust-analyzer)
        LSP-->>Prob: Update LSP Diagnostic Markers
    end

    Prob-->>UI: Aggregate Findings & Highlight Errors
    UI-->>Dev: Display in Problems Panel & Status Bar

    opt Run Code in Terminal / Output
        Dev->>UI: Trigger Run (F5)
        UI->>Term: Spawn QProcess (cmd/powershell/bash)
        Term-->>Dev: Stream Output & Error Codes
    end
```

---

## Key Capabilities & Runtime Invariants

| Capability / Principle | Implementation Details | Guarantee / Invariant |
| --- | --- | --- |
| **Local-First & Zero-Egress** | Core editor, syntax highlighters, plugins, and terminal run 100% offline. | Zero telemetry, zero external network requests during standard editing. |
| **Non-Elevation (User Mode)** | Runs entirely in unprivileged user space. | No administrative or root privileges requested. |
| **Multi-Language Highlighting** | Universal regex engine (`UniversalHighlighter`) with boundary escaping. | Python, JavaScript, TypeScript, C++, Rust, Go, Java, and custom plugins. |
| **Extensible Plugin System** | Declarative JSON format (`plugins/*.json`) and dynamic Python classes. | Hot-reloading and auto-discovery without modifying core source files. |
| **LSP Diagnostics & Completion** | Thread-safe Qt client communicating with standard Language Servers over stdin/stdout. | Non-blocking UI; handles pylsp, typescript-language-server, rust-analyzer, clangd, gopls. |
| **Background Linting** | Asynchronous execution of local linters (Ruff, flake8, ESLint) on save. | Errors and warnings aggregated dynamically in unified Problems Panel. |
| **Save-Failure Resilience** | Guarded filesystem write operations with buffer preservation. | Tabs remain open and unsaved state is protected if filesystem write fails. |
| **Integrated Terminal** | Embedded `QProcess` terminal supporting `cmd`, `PowerShell`, and `bash`. | Dynamic encoding adaptation (cp1252 / utf-8) and working directory synchronisation. |

---

## Visual Showcase

![CodeBox Main Window](README/screenshots/main.png)
*Figure 1: CodeBox desktop interface featuring the project navigation tree, multi-tab editor with syntax highlighting, integrated terminal, and diagnostics panel.*

---

## Features

- **Rich Syntax Highlighting**: Pre-configured highlighting for Python, JavaScript, TypeScript, C++, Rust, Go, and Java with punctuation-safe word boundary matching.
- **Declarative Plugin Architecture**: Create and extend language definitions in seconds using clean JSON schemas (`plugins/`, `~/.codebox/plugins/`).
- **Interactive Management Dialogs**: Full GUI dialogs for managing language plugins (`Ctrl+Shift+P`) and reviewing keyboard shortcuts (`F1`).
- **Integrated Terminal**: Embedded native shell with command history, output streaming, and automatic directory synchronization.
- **Project File Tree**: Tree view with proxy search filtering, context actions, and Git porcelain status badges.
- **Multi-Tab Workspace**: Drag-and-drop tab reordering, save-failure protection, and absolute path tooltips.
- **Minimap Preview & Navigation**: Synchronized minimap overview, bracket auto-pairing, and go-to-line navigation (`Ctrl+G`).
- **Dual Theme System**: Seamless light/dark palette switching powered by `features/theme_manager.py`.
- **LSP Diagnostics & Completion**: Asynchronous background queries providing real-time diagnostics and code completions.
- **Automated Linters**: On-save Ruff, flake8, and ESLint integration piped directly to the unified Problems Panel.

---

## Installation & Quickstart

```bash
# Clone the repository
git clone https://github.com/dev-bricks/CodeBox.git
cd CodeBox

# Install runtime dependencies
pip install -r requirements.txt

# Launch CodeBox
python main.py
```

On Windows, you can also launch CodeBox by double-clicking `start.bat`.

### System Requirements

- **Python**: 3.10, 3.11, 3.12, or 3.13
- **GUI Framework**: PySide6 >= 6.5.0
- **Operating Systems**: Windows 10/11, POSIX Linux (Ubuntu, Debian, Fedora), macOS

---

## Language Server Protocol (LSP) Setup

CodeBox connects directly to standard Language Servers installed on your system:

| Language | Recommended Language Server | Installation Command |
| --- | --- | --- |
| **Python** | `python-lsp-server` (pylsp) | `pip install "python-lsp-server[all]"` |
| **TypeScript / JS** | `typescript-language-server` | `npm install -g typescript-language-server typescript` |
| **Rust** | `rust-analyzer` | `rustup component add rust-analyzer` |
| **Go** | `gopls` | `go install golang.org/x/tools/gopls@latest` |
| **C / C++** | `clangd` | Install LLVM / Clang package |

CodeBox prioritizes servers on your system `PATH` and automatically falls back to `python -m pylsp` when running in virtual environments.

---

## Declarative Plugin System

Define custom languages easily by placing a JSON file into `plugins/` or `~/.codebox/plugins/`:

```json
{
  "name": "CustomLang",
  "version": "1.0.0",
  "extensions": [".custom", ".cst"],
  "keywords": ["function", "end", "if", "then", "else", "return"],
  "comment_style": ["#"],
  "auto_close_pairs": {
    "(": ")",
    "[": "]",
    "{": "}"
  }
}
```

Reload plugins at runtime via the Plugin Manager (`Ctrl+Shift+P`).

---

## Local Windows Build

Compile a standalone, zero-dependency Windows executable:

```bat
build_exe.bat
```

The build script uses PyInstaller with `CodeBox.spec` to bundle application icons, default themes, and declarative plugins into `dist\CodeBox.exe`.

---

## Project Structure

```text
CodeBox/
├── main.py                  # Application entry point & CLI parameter parser
├── version.py               # Central version constants & window title formatter
├── pyproject.toml           # PEP 621 packaging metadata & pytest configuration
├── requirements.txt         # Production runtime dependencies (PySide6)
├── core/                    # Core editor tabs, highlighter, minimap, output panel
├── features/                # Terminal, project tree, LSP manager, linter, themes, plugins
├── languages/               # Language definitions, providers, and declarative parser
├── ui/                      # MainWindow layout, settings, shortcuts, and plugin dialogs
├── plugins/                 # Bundled declarative language plugins (JSON)
├── themes/                  # QSS stylesheets (dark.qss, light.qss)
├── assets/                  # High-resolution vector banners and desktop icons
├── tests/                   # Comprehensive automated test suite (115+ tests)
└── README/screenshots/      # Visual showcase assets
```

---

## Sibling Ecosystem

CodeBox integrates with the **dev-bricks** and **ellmos-ai** developer tooling ecosystem under the **open-bricks** umbrella:

| Repository | Focus Area | Ecosystem |
| --- | --- | --- |
| [dev-bricks/safe-start-for-codex](https://github.com/dev-bricks/safe-start-for-codex) | Startup gating utility for local Codex automations | `dev-bricks` |
| [dev-bricks/companion-for-agy](https://github.com/dev-bricks/companion-for-agy) | Node.js orchestration wrapper for Antigravity | `dev-bricks` |
| [dev-bricks/automation-master](https://github.com/dev-bricks/automation-master) | Task orchestration and automation supervisor | `dev-bricks` |
| [dev-bricks/automizer-for-claude-desktop](https://github.com/dev-bricks/automizer-for-claude-desktop) | Automation bridge for Claude Desktop | `dev-bricks` |
| [ellmos-ai/ellmos-codecommander-mcp](https://github.com/ellmos-ai/ellmos-codecommander-mcp) | AST analysis, refactoring, and code diagnosis MCP server | `ellmos-ai` |
| [ellmos-ai/ellmos-filecommander-mcp](https://github.com/ellmos-ai/ellmos-filecommander-mcp) | Safe filesystem manipulation and process supervisor MCP | `ellmos-ai` |
| [doc-bricks/CleanMarkdown](https://github.com/doc-bricks/CleanMarkdown) | Modern distraction-free Markdown desktop editor | `doc-bricks` |
| [file-bricks/ExplorerPro](https://github.com/file-bricks/ExplorerPro) | Multi-tab local desktop file manager | `file-bricks` |
| [open-bricks/.github](https://github.com/open-bricks/.github) | Umbrella open-source organization and standards | `open-bricks` |

---

## Search & Disambiguation

When searching for CodeBox, use precise keywords to differentiate from older unrelated repositories:

- `dev-bricks CodeBox`
- `CodeBox PySide6 desktop IDE`
- `local-first code editor Python Windows`
- `PySide6 code editor with LSP diagnostics`
- `lightweight offline code editor Python`
- `CodeBox declarative language plugin system`

---

## Security & Privacy

CodeBox adheres to strict security and privacy standards. Review [SECURITY.md](SECURITY.md) for full details:

- **100% Offline Runtime**: No tracking, telemetry, or unsolicited cloud communication.
- **Unprivileged Operation**: Runs strictly within standard user permissions.
- **Confidential Reporting**: Vulnerabilities should be reported privately via [GitHub Security Advisories](https://github.com/dev-bricks/CodeBox/security/advisories/new) or by emailing `security@ellmos.ai` and `lukas@open-bricks.org`.

---

## License & Liability

This project is licensed under the [MIT License](LICENSE).

### Liability Disclaimer

This software is provided as an unpaid open-source contribution under Sections 516 et seq. of the German Civil Code (BGB). Pursuant to Section 521 BGB, liability is limited to intent and gross negligence. No warranty, availability guarantee, or fitness for any specific purpose is assumed.
