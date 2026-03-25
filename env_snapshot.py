#!/usr/bin/env python3
"""
Environment Variable Snapshot Tool

Capture and restore environment variable snapshots for development workflows.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_SNAPSHOT_DIR = Path.home() / ".env-snapshots"


def validate_snapshot_name(name):
    """Validate snapshot name for safety and correctness."""
    if not name:
        raise ValueError("Snapshot name cannot be empty")

    if not isinstance(name, str):
        raise ValueError("Snapshot name must be a string")

    if len(name) > 255:
        raise ValueError("Snapshot name must be 255 characters or less")

    if os.sep in name or (os.altsep and os.altsep in name):
        raise ValueError("Snapshot name cannot contain path separators")

    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
    for char in invalid_chars:
        if char in name:
            raise ValueError(f"Snapshot name cannot contain '{char}'")

    if name.startswith('-'):
        raise ValueError("Snapshot name cannot start with a hyphen")

    if name in ('.', '..'):
        raise ValueError("Snapshot name cannot be '.' or '..'")

    return True


def get_snapshot_dir(snapshot_dir=None):
    """Get the snapshot directory, creating it if needed."""
    if snapshot_dir is None:
        snapshot_dir = DEFAULT_SNAPSHOT_DIR
    
    snapshot_path = Path(snapshot_dir).expanduser()
    snapshot_path.mkdir(parents=True, exist_ok=True)
    return snapshot_path


def capture_snapshot(name, snapshot_dir=None, include_patterns=None, exclude_patterns=None):
    """Capture current environment variables to a snapshot file."""
    validate_snapshot_name(name)
    snapshot_path = get_snapshot_dir(snapshot_dir)
    
    env_vars = dict(os.environ)
    
    if include_patterns:
        filtered_vars = {}
        for pattern in include_patterns:
            for key, value in env_vars.items():
                if pattern in key:
                    filtered_vars[key] = value
        env_vars = filtered_vars
    
    if exclude_patterns:
        for pattern in exclude_patterns:
            env_vars = {k: v for k, v in env_vars.items() if pattern not in k}
    
    timestamp = datetime.now().isoformat()
    snapshot_data = {
        "name": name,
        "timestamp": timestamp,
        "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
        "variables": env_vars
    }
    
    filename = f"{name}.json"
    filepath = snapshot_path / filename
    
    with open(filepath, 'w') as f:
        json.dump(snapshot_data, f, indent=2, sort_keys=True)
    
    print(f"Snapshot '{name}' captured with {len(env_vars)} variables")
    print(f"Saved to: {filepath}")
    return filepath


def restore_snapshot(name, snapshot_dir=None, overwrite=False):
    """Restore environment variables from a snapshot file."""
    validate_snapshot_name(name)
    snapshot_path = get_snapshot_dir(snapshot_dir)
    filepath = snapshot_path / f"{name}.json"
    
    if not filepath.exists():
        print(f"Error: Snapshot '{name}' not found at {filepath}", file=sys.stderr)
        sys.exit(1)
    
    with open(filepath, 'r') as f:
        snapshot_data = json.load(f)
    
    variables = snapshot_data.get("variables", {})
    restored_count = 0
    skipped_count = 0
    
    for key, value in variables.items():
        if key not in os.environ or overwrite:
            os.environ[key] = value
            restored_count += 1
        else:
            skipped_count += 1
    
    print(f"Restored {restored_count} variables from snapshot '{name}'")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} existing variables (use --overwrite to force)")
    
    return restored_count


def list_snapshots(snapshot_dir=None):
    """List all available snapshots."""
    if snapshot_dir is not None:
        validate_snapshot_name(snapshot_dir)
    snapshot_path = get_snapshot_dir(snapshot_dir)
    
    snapshots = list(snapshot_path.glob("*.json"))
    
    if not snapshots:
        print("No snapshots found")
        return []
    
    print(f"Available snapshots in {snapshot_path}:")
    print("-" * 60)
    
    snapshot_info = []
    for filepath in sorted(snapshots):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            name = data.get("name", filepath.stem)
            timestamp = data.get("timestamp", "unknown")
            var_count = len(data.get("variables", {}))
            snapshot_info.append({
                "name": name,
                "timestamp": timestamp,
                "variables": var_count,
                "path": filepath
            })
            print(f"  {name}")
            print(f"    Created: {timestamp}")
            print(f"    Variables: {var_count}")
            print()
        except (json.JSONDecodeError, IOError) as e:
            print(f"  {filepath.stem} (corrupted: {e})")
            print()
    
    return snapshot_info


def show_diff(name1, name2, snapshot_dir=None):
    """Show differences between two snapshots."""
    validate_snapshot_name(name1)
    validate_snapshot_name(name2)
    snapshot_path = get_snapshot_dir(snapshot_dir)
    
    files = []
    for name in [name1, name2]:
        filepath = snapshot_path / f"{name}.json"
        if not filepath.exists():
            print(f"Error: Snapshot '{name}' not found", file=sys.stderr)
            sys.exit(1)
        with open(filepath, 'r') as f:
            files.append(json.load(f))
    
    vars1 = files[0].get("variables", {})
    vars2 = files[1].get("variables", {})
    
    keys1 = set(vars1.keys())
    keys2 = set(vars2.keys())
    
    only_in_first = keys1 - keys2
    only_in_second = keys2 - keys1
    common_keys = keys1 & keys2
    
    changed = []
    for key in common_keys:
        if vars1[key] != vars2[key]:
            changed.append(key)
    
    print(f"Comparison: {name1} vs {name2}")
    print("=" * 60)
    
    if only_in_first:
        print(f"\nOnly in {name1} ({len(only_in_first)}):")
        for key in sorted(only_in_first):
            print(f"  - {key}")
    
    if only_in_second:
        print(f"\nOnly in {name2} ({len(only_in_second)}):")
        for key in sorted(only_in_second):
            print(f"  + {key}")
    
    if changed:
        print(f"\nChanged values ({len(changed)}):")
        for key in sorted(changed):
            print(f"  ~ {key}")
            print(f"      {name1}: {vars1[key][:50]}..." if len(vars1[key]) > 50 else f"      {name1}: {vars1[key]}")
            print(f"      {name2}: {vars2[key][:50]}..." if len(vars2[key]) > 50 else f"      {name2}: {vars2[key]}")
    
    if not only_in_first and not only_in_second and not changed:
        print("No differences found")
    
    return {
        "only_in_first": len(only_in_first),
        "only_in_second": len(only_in_second),
        "changed": len(changed)
    }


def delete_snapshot(name, snapshot_dir=None):
    """Delete a snapshot file."""
    validate_snapshot_name(name)
    snapshot_path = get_snapshot_dir(snapshot_dir)
    filepath = snapshot_path / f"{name}.json"
    
    if not filepath.exists():
        print(f"Error: Snapshot '{name}' not found", file=sys.stderr)
        sys.exit(1)
    
    filepath.unlink()
    print(f"Deleted snapshot '{name}'")
    return True


def export_snapshot(name, output_file, snapshot_dir=None):
    """Export snapshot variables to a shell sourceable file."""
    validate_snapshot_name(name)
    snapshot_path = get_snapshot_dir(snapshot_dir)
    filepath = snapshot_path / f"{name}.json"
    
    if not filepath.exists():
        print(f"Error: Snapshot '{name}' not found", file=sys.stderr)
        sys.exit(1)
    
    with open(filepath, 'r') as f:
        snapshot_data = json.load(f)
    
    variables = snapshot_data.get("variables", {})
    
    output_path = Path(output_file).expanduser()
    with open(output_path, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Exported from snapshot '{name}'\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
        for key, value in sorted(variables.items()):
            escaped_value = value.replace("'", "'\"'\"'")
            f.write(f"export {key}='{escaped_value}'\n")
    
    print(f"Exported {len(variables)} variables to {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Capture and restore environment variable snapshots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s capture dev-session
  %(prog)s restore dev-session
  %(prog)s list
  %(prog)s diff before-deploy after-deploy
  %(prog)s export prod-vars ./load_env.sh
        """
    )
    
    parser.add_argument(
        "--snapshot-dir",
        help=f"Directory to store snapshots (default: {DEFAULT_SNAPSHOT_DIR})"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    capture_parser = subparsers.add_parser("capture", help="Capture current environment")
    capture_parser.add_argument("name", help="Snapshot name")
    capture_parser.add_argument(
        "--include", "-i",
        action="append",
        help="Include only variables containing this pattern"
    )
    capture_parser.add_argument(
        "--exclude", "-e",
        action="append",
        help="Exclude variables containing this pattern"
    )
    
    restore_parser = subparsers.add_parser("restore", help="Restore from snapshot")
    restore_parser.add_argument("name", help="Snapshot name")
    restore_parser.add_argument(
        "--overwrite", "-o",
        action="store_true",
        help="Overwrite existing environment variables"
    )
    
    subparsers.add_parser("list", help="List available snapshots")
    
    diff_parser = subparsers.add_parser("diff", help="Compare two snapshots")
    diff_parser.add_argument("snapshot1", help="First snapshot name")
    diff_parser.add_argument("snapshot2", help="Second snapshot name")
    
    delete_parser = subparsers.add_parser("delete", help="Delete a snapshot")
    delete_parser.add_argument("name", help="Snapshot name to delete")
    
    export_parser = subparsers.add_parser("export", help="Export to shell script")
    export_parser.add_argument("name", help="Snapshot name")
    export_parser.add_argument("output", help="Output file path")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "capture":
            capture_snapshot(
                args.name,
                args.snapshot_dir,
                args.include,
                args.exclude
            )
        elif args.command == "restore":
            restore_snapshot(args.name, args.snapshot_dir, args.overwrite)
        elif args.command == "list":
            list_snapshots(args.snapshot_dir)
        elif args.command == "diff":
            show_diff(args.snapshot1, args.snapshot2, args.snapshot_dir)
        elif args.command == "delete":
            delete_snapshot(args.name, args.snapshot_dir)
        elif args.command == "export":
            export_snapshot(args.name, args.output, args.snapshot_dir)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
