# Cross-Platform Development

This project is designed so Windows and macOS can share code through Git while
keeping machine-specific files local.

## What Should Go Into Git

- Source code in `automation/`, `frontend/`, `scripts/`, and `docs/`
- Frontend lockfile: `frontend/pnpm-lock.yaml`
- Public build output in `site/`
- Example configuration such as `.env.example`

## What Must Stay Local

- `.env`
- `.venv/`
- `frontend/node_modules/`
- `data/`
- Downloaded reports: `.xlsx`, `.csv`, `.zip`
- Browser login state such as `alimama_state.json`

These are already covered by `.gitignore`.

## First-Time Setup On Each Computer

Use the same commands on Windows and macOS:

```bash
python scripts/dev.py setup
cp .env.example .env
```

On Windows PowerShell, copy the env file with:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` so its paths point to files on that computer.

## Daily Commands

```bash
python scripts/dev.py login
python scripts/dev.py daily-once
python scripts/dev.py dev
python scripts/dev.py check
python scripts/dev.py deploy
```

`daily-once` downloads yesterday's report, updates the local Excel data, builds
the dashboard, commits public site changes, and pushes them. Use `daily-loop`
only on the computer that should keep running the scheduled daily job.

## Two-Computer Workflow

Before starting work:

```bash
git pull
```

After changing code or public dashboard output:

```bash
python scripts/dev.py check
git status
git add <files>
git commit -m "your message"
git push
```

On the other computer:

```bash
git pull
python scripts/dev.py setup
```

You normally only need `setup` again after dependencies change.

## Important Rule

Do not commit local `.env`, raw reports, Excel source files, or login state.
Those files are expected to be different on your MacBook and Windows computer.
