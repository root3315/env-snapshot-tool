# env-snapshot-tool

Quick tool to capture and restore environment variable snapshots. Because switching between projects and forgetting to set that one weird env var is the worst.

## Why does this exist

You know the drill:
- Working on `project-a` with a bunch of env vars set
- Switch to `project-b`, terminal gets messy
- Come back to `project-a` next day, nothing works
- Spend 20 minutes hunting down which env var you forgot

This tool lets you snapshot your environment and restore it later. One command, done.

## Installation

No dependencies needed - it's just Python stdlib.

```bash
chmod +x env_snapshot.py
./env_snapshot.py --help
```

Or add an alias to your shell config:

```bash
alias env-snap='python3 ~/path/to/env_snapshot.py'
```

## Quick Start

### Capture a snapshot

```bash
./env_snapshot.py capture my-project
```

This saves all current environment variables to `~/.env-snapshots/my-project.json`.

Want to be selective?

```bash
# Only capture vars containing certain patterns
./env_snapshot.py capture aws-session --include AWS --include ARN

# Exclude sensitive stuff
./env_snapshot.py capture clean-env --exclude SECRET --exclude PASSWORD --exclude KEY
```

### Restore a snapshot

```bash
./env_snapshot.py restore my-project
```

By default it won't overwrite existing vars. Force it if you need:

```bash
./env_snapshot.py restore my-project --overwrite
```

### List snapshots

```bash
./env_snapshot.py list
```

Shows all your saved snapshots with timestamps and variable counts.

### Compare snapshots

```bash
./env_snapshot.py diff before-deploy after-deploy
```

Useful to see what changed between environments or before/after some config change.

### Export to shell script

```bash
./env_snapshot.py export prod-vars ./load_prod.sh
source ./load_prod.sh
```

Generates a sourceable bash script with all the exports.

### Delete a snapshot

```bash
./env_snapshot.py delete old-project
```

## Where stuff is stored

Snapshots live in `~/.env-snapshots/` by default. You can override with `--snapshot-dir`:

```bash
./env_snapshot.py capture team-shared --snapshot-dir /shared/team/envs
```

## Real workflow examples

### Switch between AWS profiles

```bash
# Morning: capture your dev environment
./env_snapshot.py capture dev

# Need to test prod stuff
./env_snapshot.py capture prod --include AWS

# Switch between them
./env_snapshot.py restore dev
./env_snapshot.py restore prod
```

### Before messing with environment

```bash
# About to run some sketchy script
./env_snapshot.py capture before-mess

# Run the thing
./sketchy_script.sh

# Oops, broke something. Restore!
./env_snapshot.py restore before-mess --overwrite
```

### Share env setup with teammate

```bash
# Capture your working setup
./env_snapshot.py capture working-setup

# Export it
./env_snapshot.py export working-setup setup.sh

# Send them the file
scp setup.sh teammate@host:~/
```

## Notes

- Snapshots are just JSON files, feel free to peek/edit them
- No encryption - don't snapshot secrets you wouldn't commit to git
- Works on Linux and macOS (haven't tested Windows, PRs welcome)

## License

Do whatever you want with it.
