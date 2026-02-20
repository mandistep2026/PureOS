# PureOS Developer Guide

This guide is for contributors who want to understand, extend, test, and maintain PureOS.

## 1) Project Goals and Constraints

PureOS is intentionally built with **Python standard library only**. The project prioritizes:

- Educational clarity over complex optimizations
- Predictable behavior and testability
- Unix-like command ergonomics
- Backward compatibility for shell behavior and scripts

### Core Constraint: No Third-Party Dependencies

Do not introduce external packages. New features should use built-in modules only.

---

## 2) Repository Layout

```text
PureOS/
├── main.py                     # Application entry point and CLI flow
├── core/                       # Kernel, filesystem, auth, persistence, IPC, metrics, etc.
├── shell/                      # Shell parser, command implementations, completion
├── tests/                      # Unit + integration test suite (unittest)
├── docs/                       # User/developer/API documentation
├── README.md                   # High-level overview and release notes
└── CHANGELOG_v2.1.md           # Quality/stability release details
```

### `core/` module responsibilities

- `kernel.py`: process lifecycle, scheduling, system state hooks
- `filesystem.py`: in-memory filesystem, paths, permissions, metadata
- `user.py` + `auth.py`: user accounts, authentication, session flow
- `persistence.py`: save/load state to `~/.pureos/state.json`
- `package.py`: package metadata and install/remove workflows
- `network.py`: network abstractions used by shell networking commands
- `metrics.py`, `logging.py`, `limits.py`, `ipc.py`, `cron.py`, `jobs.py`: observability + runtime services

### `shell/` module responsibilities

- `shell.py`: command registration, parsing, expansion, dispatch
- `scripting.py`: script execution support
- `completion.py`: interactive line editing/completion
- `pkgcommand.py`, `netcommand.py`, `systemcommands.py`, `monitorcommands.py`: grouped command families

---

## 3) Local Development Setup

## Prerequisites

- Python 3.8+ (3.10+ recommended)
- No virtual environment required (and no pip dependencies expected)

## Run interactive shell

```bash
python main.py
```

## Run a batch file

```bash
python main.py --batch demo_script.sh
```

## Run built-in smoke tests

```bash
python main.py --test
```

---

## 4) Test Strategy and Commands

PureOS uses `unittest` with a split between **unit** and **integration** tests.

## Canonical test runner

```bash
python tests/run_tests.py
```

Useful options:

```bash
python tests/run_tests.py -v
python tests/run_tests.py --filter filesystem
python tests/run_tests.py --start-dir tests/unit
```

## Direct unittest execution

```bash
python -m unittest tests.unit.test_filesystem
python -m unittest tests.integration.test_shell_core
```

### What to validate before opening a PR

1. New/changed behavior has test coverage
2. Existing tests still pass
3. Docs are updated when command behavior/flags/output changes
4. No external dependency was introduced

---

## 5) Architecture Overview

## Boot and runtime flow (`main.py`)

1. Initialize `Kernel`
2. Mount `FileSystem`
3. Initialize `UserManager` and `Authenticator`
4. Initialize `Shell` with core services
5. Offer persisted-state restore (if present)
6. Enter login prompt (interactive mode)
7. Run shell loop
8. Auto-save on shutdown

## Shell execution pipeline (`shell/shell.py`)

1. Input read from terminal/batch/script
2. Alias expansion
3. Environment expansion (`$VAR`, `${VAR}`, `$?`, arithmetic/command substitution)
4. Tokenization (`shlex`)
5. Wildcard expansion (with command-specific guards)
6. Command lookup and execution
7. Exit status persisted in shell state

## Service extension points

The shell bootstraps optional subsystems (`jobs`, package manager, networking, monitoring commands) using safe imports so features degrade gracefully if a module is unavailable.

---

## 6) Adding or Updating Commands

## Where to implement

- Core built-ins: `shell/shell.py`
- Domain families:
  - Package commands: `shell/pkgcommand.py`
  - Network commands: `shell/netcommand.py`
  - System/ops commands: `shell/systemcommands.py`
  - Monitoring/diagnostics: `shell/monitorcommands.py`

## Implementation pattern

1. Add a class extending `ShellCommand`
2. Implement `execute(self, args, shell) -> int`
3. Return conventional exit codes (`0` success, non-zero error)
4. Register command in `Shell._register_commands()`
5. Add/adjust tests in unit/integration suites
6. Update docs (`README.md`, `docs/USER_GUIDE.md`, `docs/API_REFERENCE.md` as needed)

### Behavioral consistency guidelines

- Match familiar Unix flag names where practical
- Keep error messages actionable and concise
- Avoid silently swallowing user-facing failures
- Preserve backward-compatible output when possible

---

## 7) Filesystem and State Considerations

## Filesystem behavior (`core/filesystem.py`)

When changing filesystem logic, verify:

- Path normalization for relative/absolute paths
- Ownership and permission checks
- Type-specific operations (file vs directory vs link)
- Metadata updates (timestamps, size where relevant)

## Persistence behavior (`core/persistence.py`)

State save/load should remain resilient:

- Missing/partial state files should fail gracefully
- New state keys should be backward-compatible
- Shell history/env/aliases/cwd should restore consistently

---

## 8) Authentication and Multi-User Changes

Relevant modules:

- `core/user.py`
- `core/auth.py`
- Shell commands: `useradd`, `userdel`, `passwd`, `su`, `login`, `logout`, `who`, `id`, `groups`

When modifying auth/user code:

- Validate username and password handling paths
- Ensure privilege-sensitive operations still gate correctly
- Confirm session context updates shell environment (`USER`, `HOME`) correctly
- Add regression tests for both success and failure flows

---

## 9) Documentation Update Checklist

For behavior changes, update all affected docs in the same PR:

- `README.md` for high-level capability changes
- `docs/USER_GUIDE.md` for usage examples and common workflows
- `docs/API_REFERENCE.md` for public interfaces and command option tables
- `CHANGELOG_v2.1.md` (or next changelog file) for release-level notes

Keep examples executable and aligned with current output conventions.

---

## 10) Contribution Workflow (Recommended)

1. Create a focused branch
2. Implement minimal scoped changes
3. Add or update tests
4. Run full test suite
5. Update docs
6. Commit with clear message
7. Open PR summarizing:
   - What changed
   - Why it changed
   - How it was tested
   - Any compatibility notes

---

## 11) Common Pitfalls

- Forgetting to register new commands in `Shell._register_commands()`
- Updating command behavior without updating docs/tests
- Introducing output changes that break integration tests
- Using non-stdlib imports
- Handling parsing edge cases inconsistently with existing shell semantics

---

## 12) Quick Command Reference for Contributors

```bash
# Run shell
python main.py

# Run full test suite
python tests/run_tests.py

# Run a subset
python tests/run_tests.py --filter shell

# Run one test module
python -m unittest tests.integration.test_shell_core
```

If you are unsure where to place a change, start by tracing from `main.py` into `shell/shell.py` and then into the specific `core/` or `shell/*command.py` module for the affected behavior.
