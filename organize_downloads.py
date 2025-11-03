#!/usr/bin/env python3
"""
organize_downloads.py

Production-ready file organizer for your Downloads folder.
Features:
- Reads categories from config.json
- Dry-run (preview) mode
- Safe move with collision handling
- Logging + undo capability
- Cross-platform (Windows/macOS/Linux)
"""

from __future__ import annotations
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# -----------------------------
# Configuration Handling
# -----------------------------
def expand_path(path_str: str) -> Path:
    return Path(os.path.expanduser(path_str)).resolve()


def load_config(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "DownloadsPath": raw.get("DownloadsPath", "~/Downloads"),
        "Categories": raw.get("Categories", {}),
        "LargeFileThresholdMB": raw.get("LargeFileThresholdMB", 500),
        "Ignore": raw.get("Ignore", []),
        "LogFile": raw.get("LogFile", "logs/organize.log"),
        "ActionLogFile": raw.get("ActionLogFile", "logs/actions.jsonl"),
    }


# -----------------------------
# Logging Setup
# -----------------------------
def build_logger(log_path: Path, verbose: bool = False) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("organizer")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(log_path, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(handler)

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter("%(message)s"))
        console.setLevel(logging.DEBUG if verbose else logging.INFO)
        logger.addHandler(console)
    return logger


# -----------------------------
# Utility Functions
# -----------------------------
def file_extension_lower(path: Path) -> str:
    return path.suffix.lower()


def find_category(ext: str, categories: Dict[str, List[str]]) -> str:
    for cat, exts in categories.items():
        if ext in (e.lower() for e in exts):
            return cat
    return "Others"


def resolve_name_collision(dest: Path) -> Path:
    if not dest.exists():
        return dest
    parent = dest.parent
    stem, suffix = dest.stem, dest.suffix
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def safe_move(src: Path, dest: Path, logger: logging.Logger) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    final_dest = resolve_name_collision(dest)
    try:
        os.replace(src, final_dest)
    except OSError:
        shutil.move(str(src), str(final_dest))
    logger.debug(f"Moved: {src} -> {final_dest}")
    return final_dest


def record_action(action_log: Path, src: Path, dest: Path):
    action_log.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "src": str(src),
        "dest": str(dest),
    }
    with action_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# -----------------------------
# Core Functions
# -----------------------------
def scan_folder(target: Path, ignore: List[str]) -> List[Path]:
    return [p for p in target.iterdir() if p.is_file() and p.name not in ignore]


def organize(config: dict, dry_run=False, verbose=False, preview_limit: Optional[int] = None) -> Dict[str, int]:
    downloads = expand_path(config["DownloadsPath"])
    logger = build_logger(expand_path(config["LogFile"]), verbose)
    action_log_path = expand_path(config["ActionLogFile"])

    if not downloads.exists():
        raise FileNotFoundError(f"Target folder does not exist: {downloads}")

    categories = {k: [e.lower() for e in v] for k, v in config["Categories"].items()}
    ignore = config["Ignore"]
    files = scan_folder(downloads, ignore)

    logger.info(f"Found {len(files)} files to inspect.")
    summary = {k: 0 for k in list(categories.keys()) + ["Others"]}
    processed = 0

    for idx, file in enumerate(files):
        ext = file_extension_lower(file)
        cat = find_category(ext, categories)
        dest_folder = downloads / cat
        dest_path = dest_folder / file.name

        if config["LargeFileThresholdMB"]:
            size_mb = file.stat().st_size / (1024 * 1024)
            if size_mb >= config["LargeFileThresholdMB"]:
                dest_folder = dest_folder / "LargeFiles"
                dest_path = dest_folder / file.name
                logger.debug(f"Large file: {file.name} ({size_mb:.1f} MB)")

        if dry_run:
            logger.info(f"[DRY RUN] {file.name} -> {cat}/")
        else:
            final = safe_move(file, dest_path, logger)
            record_action(action_log_path, file, final)
            logger.info(f"Moved: {file.name} -> {final}")

        summary.setdefault(cat, 0)
        summary[cat] += 1
        processed += 1

        if preview_limit and idx + 1 >= preview_limit:
            logger.info("Preview limit reached; stopping early.")
            break

    logger.info(f"Processed {processed} files.")
    return summary


def undo_actions(config: dict, count: int, verbose=False) -> int:
    logger = build_logger(expand_path(config["LogFile"]), verbose)
    action_log = expand_path(config["ActionLogFile"])

    if not action_log.exists():
        logger.error("No action log found.")
        return 0

    lines = action_log.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        logger.error("Action log empty.")
        return 0

    to_undo = lines[-count:]
    remaining = lines[:-count]
    undone = 0

    for line in reversed(to_undo):
        try:
            entry = json.loads(line)
            src, dest = Path(entry["src"]), Path(entry["dest"])
            if dest.exists() and not src.exists():
                os.replace(dest, src)
                logger.info(f"Undone: {dest} -> {src}")
                undone += 1
        except Exception as e:
            logger.error(f"Undo failed: {e}")

    action_log.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    logger.info(f"Undone {undone} actions.")
    return undone


# -----------------------------
# CLI Interface
# -----------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Organize your Downloads folder by file type.")
    p.add_argument("--config", "-c", default="config.json", help="Path to config.json")
    p.add_argument("--dry-run", "-n", action="store_true", help="Preview only (no changes)")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    p.add_argument("--undo", "-u", type=int, default=0, help="Undo last N moves")
    p.add_argument("--preview-limit", type=int, default=0, help="Limit number of files processed (testing)")
    return p.parse_args()


def main():
    args = parse_args()
    try:
        config = load_config(Path(args.config))
    except Exception as e:
        print(f"Config load failed: {e}")
        sys.exit(1)

    if args.undo:
        undo_actions(config, args.undo, args.verbose)
        return

    summary = organize(config, args.dry_run, args.verbose, args.preview_limit or None)
    print("Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
