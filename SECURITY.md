# Security Policy

## Supported Versions

CodeBox is currently maintained on the `main` branch before a stable 1.0
release. Please test reports against the latest `main` commit when possible.

## Reporting a Vulnerability

If you find a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue**
2. **Use GitHub's [private vulnerability reporting](../../security/advisories/new)**
3. Include: description, steps to reproduce, potential impact

### How to Report

1. Go to: Repository → Security → Advisories → New
2. Fill out the form (title, description, severity, affected versions)
3. Submit privately (not visible to public until disclosed)

We will respond as soon as possible for a solo-maintained open-source project.

## Scope

Security reports are in scope when they affect CodeBox itself, especially:

- Local file access through the editor, project tree, or save/open workflows
- Terminal, Git, build, and run-tool invocation from inside the application
- Language Server Protocol process handling
- Optional SSH/SFTP remote-editing code paths
- Handling of local configuration files, credentials, logs, and build artifacts

Generated build outputs, personal local configuration, private test locks, and
secrets accidentally created by a user are not intended to be committed. The
repository `.gitignore` excludes common credential, SSH-key, database, log, and
build-artifact patterns.

## Response

As a solo project, response times may vary. Critical issues will be
prioritized. Please allow reasonable time before public disclosure.
