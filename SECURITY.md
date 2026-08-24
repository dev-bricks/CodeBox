# Security Policy / Sicherheitsrichtlinie

[English](#english) | [Deutsch](#deutsch)

---

<a id="english"></a>
## English

### Supported Versions

CodeBox is maintained on the `main` branch. Active security maintenance is provided for the current development line:

| Version | Supported | Notes |
| ------- | --------- | ----- |
| `0.1.x` | :white_check_mark: | Current active development line |
| `< 0.1` | :x: | Unsupported legacy versions |

### Reporting a Vulnerability

If you discover a security vulnerability in CodeBox, please report it responsibly:

1. **Do NOT open a public GitHub issue.**
2. **Use GitHub's [Private Vulnerability Reporting](https://github.com/dev-bricks/CodeBox/security/advisories/new)** to submit your findings confidentially.
3. If GitHub Advisories is unavailable, contact the maintainers directly via email:
   - `security@ellmos.ai`
   - `lukas@open-bricks.org`
   - `support@lukasgeiger.com`

Please include:
- A description of the vulnerability and potential impact
- Step-by-step reproduction instructions or a minimal proof-of-concept
- Affected operating system and CodeBox version

### Security Scope & Runtime Invariants

CodeBox is built around a strict **local-first, zero-egress** architecture:

- **100% Offline & Local-First**: The core editor operates entirely on local files without outbound network requests, cloud dependencies, analytics, or background telemetry.
- **Unprivileged User Mode (Non-Elevation)**: CodeBox runs within standard user permissions and never requests administrative elevation (`sudo` / UAC escalation).
- **Process & Subprocess Boundaries**: Integrated terminal shells (`cmd`, `powershell`, `bash`), build runners, and optional LSP servers run strictly under the invoking user's security context.
- **Filesystem Isolation**: File access is strictly bounded to paths explicitly chosen or opened by the user in the editor tabs or project tree.
- **Credential & Secret Protection**: Working credentials, SSH keys, session files, logs, and build artifacts are strictly excluded via `.gitignore`.

---

<a id="deutsch"></a>
## Deutsch

### Unterstützte Versionen

CodeBox wird kontinuierlich auf dem `main`-Branch gepflegt. Sicherheitsrelevante Korrekturen werden für den aktuellen Entwicklungszweig bereitgestellt:

| Version | Unterstützt | Hinweise |
| ------- | ----------- | -------- |
| `0.1.x` | :white_check_mark: | Aktiver Entwicklungszweig |
| `< 0.1` | :x: | Nicht mehr unterstützte Vorversionen |

### Schwachstelle melden

Wenn Sie eine Sicherheitslücke in CodeBox entdecken, melden Sie diese bitte verantwortungsvoll:

1. **Erstellen Sie KEIN öffentliches GitHub-Issue.**
2. Nutzen Sie die **[Private Sicherheitsmeldung (GitHub Advisories)](https://github.com/dev-bricks/CodeBox/security/advisories/new)** für eine vertrauliche Meldung.
3. Alternativ erreichen Sie das Sicherheitsteam direkt per E-Mail:
   - `security@ellmos.ai`
   - `lukas@open-bricks.org`
   - `support@lukasgeiger.com`

Bitte fügen Sie Ihrer Meldung folgende Informationen bei:
- Beschreibung der Schwachstelle und möglicher Auswirkungen
- Schritt-für-Schritt-Anleitung zur Reproduktion oder Minimalbeispiel
- Verwendetes Betriebssystem und CodeBox-Versionsnummer

### Sicherheitsarchitektur & Laufzeitinvarianten

CodeBox folgt strengen **Local-First- und Zero-Egress-Prinzipien**:

- **100% Offline & Local-First**: Der Editor arbeitet vollständig lokal ohne Netzwerkaufrufe, Cloud-Zwang, Tracking oder Telemetrie.
- **Keine Administratorrechte (Non-Elevation)**: CodeBox erfordert zu keinem Zeitpunkt administrative Privilegien oder UAC-/Root-Eskalation.
- **Prozessgrenzen & Subprozess-Sicherheit**: Terminal-Prozesse, Build-Aufrufe und optionale lokale Language-Server (LSP) laufen isoliert im normalen Benutzerkontext.
- **Dateisystem-Integrität**: Lese- und Schreibzugriffe sind strikt auf Dateien beschränkt, die explizit vom Nutzer im Projektbaum oder Editor ausgewählt wurden.
- **Geheimnisschutz**: SSH-Schlüssel, Passwörter, lokale Konfigurationen und Build-Artefakte werden über `.gitignore` vom Repository ferngehalten.
