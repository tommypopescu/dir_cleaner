import os
import time
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple

SECONDS_PER_DAY = 86400

def is_under_base(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False

def human_size(num_bytes: int) -> str:
    for unit in ['B','KB','MB','GB','TB']:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} PB"

def should_exclude(path: Path, excludes: List[str]) -> bool:
    ps = str(path)
    return any(ex in ps for ex in excludes)

def dir_stats(base_path: Path, excludes: Optional[List[str]] = None, unused_days: Optional[int] = None) -> Dict[str, int | bool]:
    excludes = excludes or []
    total_size = 0
    file_count = 0
    dir_count = 0
    old_files_count = 0
    now = time.time()
    threshold_sec = (unused_days or 0) * SECONDS_PER_DAY

    for root, dirs, files in os.walk(base_path, onerror=lambda e: None):
        root_path = Path(root)
        if should_exclude(root_path, excludes):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not should_exclude(root_path / d, excludes)]
        dir_count += len(dirs)
        for f in files:
            p = root_path / f
            if should_exclude(p, excludes):
                continue
            try:
                st = p.stat()
                total_size += st.st_size
                file_count += 1
                if unused_days and unused_days > 0:
                    if (now - st.st_mtime) >= threshold_sec:
                        old_files_count += 1
            except (FileNotFoundError, PermissionError):
                pass

    empty = (file_count == 0 and dir_count == 0)
    return {
        "size_bytes": total_size,
        "file_count": file_count,
        "dir_count": dir_count,
        "empty": empty,
        "old_files_count": old_files_count,
        "size_h": human_size(total_size),
    }

def scan_directories(base_path: Path, excludes: Optional[List[str]] = None, size_threshold_bytes: Optional[int] = None, unused_days: Optional[int] = None, depth: int = 1) -> List[Dict]:
    excludes = excludes or []
    results: List[Dict] = []
    if not base_path.exists() or not base_path.is_dir():
        return results
    to_visit: List[Tuple[Path, int]] = [(base_path, 0)]
    visited = set()
    while to_visit:
        current, d = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)
        if d < depth:
            try:
                for entry in current.iterdir():
                    if entry.is_dir() and not should_exclude(entry, excludes):
                        to_visit.append((entry, d + 1))
            except (PermissionError, FileNotFoundError):
                pass
        if current == base_path:
            continue
        stats = dir_stats(current, excludes=excludes, unused_days=unused_days)
        flagged_small = False
        if size_threshold_bytes is not None:
            flagged_small = stats["size_bytes"] < size_threshold_bytes
        results.append({
            "path": str(current),
            "rel_path": str(current.relative_to(base_path)),
            "depth": d,
            **stats,
            "flag_small": flagged_small,
        })
    results.sort(key=lambda x: x["size_bytes"], reverse=True)
    return results

def delete_or_quarantine(base_path: Path, targets: List[str], quarantine_path: Optional[Path] = None, audit_log: Optional[Path] = None) -> Dict:
    base = base_path.resolve()
    moved, deleted, skipped, errors = [], [], [], []
    ts = int(time.time())
    log_lines = []
    for t in targets:
        p = Path(t)
        if not p.is_absolute():
            p = base / p
        try:
            if not is_under_base(base, p):
                skipped.append(str(p))
                continue
            if not p.exists() or not p.is_dir():
                skipped.append(str(p))
                continue
            if quarantine_path:
                quarantine_path.mkdir(parents=True, exist_ok=True)
                dest = quarantine_path / f"{p.name}__{ts}"
                shutil.move(str(p), str(dest))
                moved.append(str(dest))
                log_lines.append(f"{ts};MOVE;{p} -> {dest}")
            else:
                shutil.rmtree(p)
                deleted.append(str(p))
                log_lines.append(f"{ts};DELETE;{p}")
        except Exception as e:
            errors.append({"path": str(p), "error": str(e)})
            log_lines.append(f"{ts};ERROR;{p};{e}")
    if audit_log:
        try:
            audit_log.parent.mkdir(parents=True, exist_ok=True)
            with open(audit_log, 'a', encoding='utf-8') as f:
                for line in log_lines:
                    f.write(line + "\n")
        except Exception:
            pass
    return {"moved": moved, "deleted": deleted, "skipped": skipped, "errors": errors}
