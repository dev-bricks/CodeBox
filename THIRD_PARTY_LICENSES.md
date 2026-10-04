# Third-Party License Audit & Governance Invariants

> **Project:** CodeBox (`dev-bricks/CodeBox`)<br>
> **Repository:** [https://github.com/dev-bricks/CodeBox](https://github.com/dev-bricks/CodeBox)<br>
> **Audit Date:** 2026-09-25<br>
> **Audit Standard:** Level 1 Software Bill of Materials (SBOM) & Open-Source Governance<br>
> **Scope:** Direct runtime dependencies, Qt GUI dynamic linkage, build/packaging tooling, system API boundaries, Level 1 SBOM, and runtime safety invariants.

---

## 1. Project License & Root Notice

CodeBox is open-source software authored by Lukas Geiger and licensed under the permissive **MIT License**. Formal copyright attribution, maintainer roles, and umbrella affiliation are documented in the root [`NOTICE`](NOTICE) file.

```text
MIT License

Copyright (c) 2026 Lukas Geiger

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 2. Direct Runtime Dependencies

| Component | Requirement | Checked Version | SPDX License Identifier | Source / PyPI URL | Governance Classification |
|---|---|---:|---|---|---|
| **PySide6** | `>=6.5.0` | 6.11.1 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | [PyPI](https://pypi.org/project/PySide6/) | Permissive Qt Dynamic Link |
| **PySide6_Addons** | transitive | 6.11.1 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | [PyPI](https://pypi.org/project/PySide6-Addons/) | Permissive Qt Dynamic Link |
| **PySide6_Essentials** | transitive | 6.11.1 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | [PyPI](https://pypi.org/project/PySide6-Essentials/) | Permissive Qt Dynamic Link |
| **shiboken6** | transitive | 6.11.1 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | [PyPI](https://pypi.org/project/shiboken6/) | Permissive Qt Dynamic Link |

### LGPL-3.0 Compliance Details for PySide6 & Qt 6
CodeBox consumes PySide6 and Qt 6 exclusively through standard dynamically linked Python C-extension wheels (`shiboken6`, Qt dynamic link libraries / shared objects `.dll` / `.so` / `.dylib`). CodeBox does not statically link, modify, or recompile Qt or PySide6 internals. In accordance with Section 4 of the GNU Lesser General Public License v3 (LGPL-3.0), users and downstream developers retain full freedom to upgrade, replace, or relink compatible versions of PySide6 and Qt shared libraries within their Python environment.

---

## 3. Optional, Remote & Language Server Integration Tooling

| Component | Requirement | Checked Version | SPDX License Identifier | Source / PyPI URL | Governance Classification |
|---|---|---:|---|---|---|
| **paramiko** | `>=5.0.0` | 5.0.0 | `LGPL-2.1-or-later` | [PyPI](https://pypi.org/project/paramiko/) | Dynamic SSH2 Library (GHSA-r374-rxx8-8654 Hardened) |
| **cryptography** | transitive | 44.0.2 | `Apache-2.0 OR BSD-3-Clause` | [PyPI](https://pypi.org/project/cryptography/) | Permissive Cryptographic Foundation |
| **bcrypt** | transitive | 4.3.0 | `Apache-2.0` | [PyPI](https://pypi.org/project/bcrypt/) | Permissive Key Derivation |
| **pynacl** | transitive | 1.6.2 | `Apache-2.0` | [PyPI](https://pypi.org/project/pynacl/) | Permissive Curve25519/Ed25519 Binding |
| **python-lsp-server** | `>=1.7.0` | 1.13.0 | `MIT` | [PyPI](https://pypi.org/project/python-lsp-server/) | Permissive LSP Subprocess Server |

---

## 4. Build, Packaging & Verification Dependencies

| Component | Requirement | Checked Version | SPDX License Identifier | Source / PyPI URL | Governance Classification |
|---|---|---:|---|---|---|
| **PyInstaller** | build-only | 6.13.0 | `GPL-2.0-or-later WITH Bootloader-Exception` | [PyPI](https://pypi.org/project/PyInstaller/) | Permissive Output via Special Exception |
| **altgraph** | build-only | 0.17.4 | `MIT` | [PyPI](https://pypi.org/project/altgraph/) | Permissive Dependency Graph Utility |
| **pytest** | `>=9.1.1` | 9.1.1 | `MIT` | [PyPI](https://pypi.org/project/pytest/) | Permissive Test Harness (CVE-2025-7117 Patched) |
| **pluggy** | transitive | 1.6.0 | `MIT` | [PyPI](https://pypi.org/project/pluggy/) | Permissive Plugin Framework |
| **ruff** | dev-only | 0.15.18 | `MIT OR Apache-2.0` | [PyPI](https://pypi.org/project/ruff/) | Permissive Linter & Formatter |
| **Pillow** | dev/test | 11.1.0 | `HPND` | [PyPI](https://pypi.org/project/Pillow/) | Permissive Historical Imaging Permission |

---

## 5. Operating System Subsystem & Isolation Guarantees

### Windows OS & API Boundaries
1. **Unprivileged Execution (RunAsInvoker):** CodeBox does not declare administrative manifests (`requireAdministrator` or `highestAvailable`). The application runs under standard Windows unprivileged user space.
2. **Subprocess Sandboxing:** Integrated terminal sessions and language server connections communicate strictly via standard OS pipes (`stdin`/`stdout`/`stderr`) using `QProcess` or isolated `subprocess.Popen` threads.
3. **No Codec Leaks:** All filesystem read/write interactions default explicitly to `UTF-8` with fallback to native platform codepages (e.g. `cp1252` on legacy Windows cmd shells) without data loss.

---

## 6. Table of Governance & Runtime Safety Invariants

CodeBox enforces strict runtime invariants across all editing, diagnostics, and workspace workflows:

| Invariant Code | Category | Name & Guarantee | Verification & Enforcement Mechanism |
|---|---|---|---|
| **INV-LOCAL-01** | Privacy & Egress | **100% Local-First & Zero-Egress** | Fully offline editor core; zero telemetry, zero analytics, zero external API queries during editing. Verified by contract test `test_local_first_and_offline_invariants`. |
| **INV-NOELEV-02** | Security & Privileges | **Unprivileged User-Mode (RunAsInvoker)** | Runs strictly in standard user mode without UAC elevation. No administrative privileges required or requested. |
| **INV-PERF-02** | Performance & Startup | **Sub-Second Cold Start (<1.0s) & Native Efficiency** | Pure PySide6/C++ Qt engine ensures instant editor launch (<1s) and low memory baseline compared to Chromium/Electron editors. |
| **INV-LGPL-03** | Licensing & Isolation | **LGPL-3.0 Dynamic Linkage & Zero-Copyleft Isolation** | Dynamic linking of PySide6 runtime wheels; pure permissive MIT/Apache/BSD ecosystem integration ensures zero viral copyleft bleed into user projects. |
| **INV-CRASH-04** | State Preservation | **Save-Failure Guard & Buffer Protection** | Guarded filesystem write handlers preserve document tabs, modified flags, and in-memory buffer states if underlying disk operations fail. |
| **INV-LSP-05** | Intelligence & Concurrency | **Asynchronous LSP Subprocess Boundary** | Language server diagnostics execute in detached background worker threads; main UI event loop remains completely non-blocking. |
| **INV-TERM-06** | Terminal & Shell | **Embedded Terminal Sandboxing & Sync** | Integrated terminal executes isolated shell processes (`cmd`, `PowerShell`, `bash`) with synchronized working directory and dynamic encoding handling. |
| **INV-PLUG-07** | Extensibility | **Declarative JSON Plugin Isolation** | Language definitions, keywords, comments, and auto-close pairs load declaratively via JSON schemas without requiring runtime code compilation. |
| **INV-PORT-08** | Workspace Management | **Multi-Root Workspaces & Relative Path Portability** | Workspace state (`.codebox-workspace`) serializes relative paths, enabling seamless multi-host repository sharing across Windows, Linux, and macOS. |
| **INV-GIT-09** | Version Control | **Porcelain Git Status & Built-in Diff Viewer** | Read-only porcelain status parsing (`git status --porcelain=v1`) and side-by-side / unified diff inspection without external Git GUI dependencies. |
| **INV-SLA-10** | Governance & Support | **48-Hour Security Response SLA & § 521 BGB Statutory Compliance** | Formal 48-hour triage guarantee for security advisories and explicit German statutory liability limitation pursuant to Section 521 BGB. |

---

## 7. Trademarks & Disclaimers

- **Python** is a registered trademark of the Python Software Foundation (PSF).
- **Qt** and **PySide** are registered trademarks of The Qt Company Ltd. and its subsidiaries.
- **Windows** is a registered trademark of Microsoft Corporation in the United States and other countries.
- All other trademarks and registered trademarks are the property of their respective owners.
