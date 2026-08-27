#!/usr/bin/env python3
"""
LEGALLY SUBJECTIVE — Infinite Build Engine (LS-ENGINE-1)
Le moteur de fond. Tourne à l'infini :
  1. exécute les tâches [engine] de QUEUE.json (scaffold, fichiers, scans)
  2. garde le zéro-mock (scan des motifs interdits — loi constitutionnelle)
  3. heartbeat + état persistant (scripts/engine_state.json)
Ne meurt jamais : toute exception est loggée, le cycle suivant reprend.
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/z/my-project")
QUEUE_FILE = ROOT / "QUEUE.json"
STATE_FILE = ROOT / "scripts" / "engine_state.json"
LOG_FILE = ROOT / "scripts" / "engine.log"
WORKLOG_FILE = ROOT / "worklog.md"

CYCLE_SECONDS = 20
GUARD_EVERY_N_CYCLES = 15
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_KEEP_LINES = 1000

# Loi constitutionnelle : zéro donnée fabriquée. Motifs bannis du code.
FORBIDDEN_PATTERNS = [
    r"Math\.random\s*\(",
    r"\bmock[A-Za-z]*\b",
    r"\bLorem [Ii]psum\b",
    r"\bfake[_-]?data\b",
    r"\bplaceholder[_-]?data\b",
]
SCAN_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".css", ".html", ".sh"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".next", "dist", "build", "scripts", ".venv", "skills", "download"}
SKIP_FILES = {"BOSS.md", "BACKLOG.md", "worklog.md", "QUEUE.json"}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    """Append une ligne horodatée au log, avec rotation si trop gros."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_BYTES:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        LOG_FILE.write_text("\n".join(lines[-LOG_KEEP_LINES:]) + "\n", encoding="utf-8")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {msg}\n")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def save_state(state):
    save_json(STATE_FILE, state)


def pick_task(queue):
    for t in queue.get("tasks", []):
        if t.get("owner") == "engine" and t.get("status") == "pending":
            return t
    return None


def execute(task):
    ttype = task.get("type")
    spec = task.get("spec", {})
    if ttype == "scaffold_dirs":
        made = []
        for d in spec.get("dirs", []):
            (ROOT / d).mkdir(parents=True, exist_ok=True)
            made.append(d)
        return f"{len(made)} dossiers créés: {', '.join(made)}"
    if ttype == "scaffold_files":
        made = []
        for fdef in spec.get("files", []):
            p = ROOT / fdef["path"]
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(fdef["content"], encoding="utf-8")
                made.append(fdef["path"])
        return f"{len(made)} fichiers créés: {', '.join(made) if made else 'rien (déjà présents)'}"
    if ttype == "guard_scan":
        v = run_guard()
        return f"scan zéro-mock: {len(v)} violation(s)" + (f" → {v[:10]}" if v else " — PROPRE")
    if ttype == "heartbeat":
        return "heartbeat manuel exécuté"
    return f"type inconnu: {ttype} (ignoré)"


def run_guard():
    violations = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        if path.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for pat in FORBIDDEN_PATTERNS:
                if re.search(pat, line):
                    violations.append({"file": str(path.relative_to(ROOT)), "line": i, "pattern": pat})
        if len(violations) > 200:
            break
    return violations


def worklog_append(task, result):
    try:
        with open(WORKLOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"\n---\nTask ID: {task['id']} (engine)\n"
                f"Agent: LS-ENGINE-1\n"
                f"Task: {task.get('title', task.get('type', 'engine task'))}\n\n"
                f"Work Log:\n- {result}\n\n"
                f"Stage Summary:\n- exécuté automatiquement par le moteur de fond\n"
            )
    except Exception as e:
        log(f"worklog append failed: {e}")


def main():
    ap = argparse.ArgumentParser(description="Legally Subjective build engine")
    ap.add_argument("--once", action="store_true", help="un seul passage : exécute TOUTES les tâches engine en attente + guard, puis sort")
    ap.add_argument("--for-seconds", type=int, default=0, help="tourne N secondes puis sort proprement (résilient aux relances)")
    args = ap.parse_args()

    state = load_json(STATE_FILE, {})
    cycle = state.get("cycles", 0)
    state.update({"started": state.get("started", now_iso()), "cycles": cycle, "status": "running", "resumes": state.get("resumes", 0) + 1})
    save_state(state)
    log(f"ENGINE {'RESUME' if cycle else 'START'} — cycles cumulés: {cycle} — mode {'ONCE' if args.once else ('TIMED ' + str(args.for_seconds) + 's' if args.for_seconds else 'INFINI')}")

    deadline = time.time() + args.for_seconds if args.for_seconds else None
    while True:
        cycle += 1
        try:
            queue = load_json(QUEUE_FILE, {"tasks": []})
            task = pick_task(queue)
            if task:
                result = execute(task)
                task["status"] = "done"
                task["completed_at"] = now_iso()
                task["result"] = result[:300]
                save_json(QUEUE_FILE, queue)
                state["tasks_done"].append({"id": task["id"], "at": now_iso()})
                log(f"cycle {cycle}: TASK {task['id']} → {result}")
                worklog_append(task, result)
                if args.once and not pick_task(load_json(QUEUE_FILE, {"tasks": []})):
                    state["cycles"] = cycle
                    state["status"] = "paused-clean"
                    save_state(state)
                    log(f"ENGINE EXIT — mode ONCE terminé, cycle {cycle}")
                    return
            else:
                if cycle % GUARD_EVERY_N_CYCLES == 0:
                    v = run_guard()
                    state["last_guard"] = {"cycle": cycle, "count": len(v), "violations": v[:50]}
                    log(f"cycle {cycle}: GUARD → {len(v)} violation(s)")
                else:
                    pending_agent = sum(
                        1 for t in queue.get("tasks", []) if t.get("owner") == "agent" and t.get("status") == "pending"
                    )
                    log(f"cycle {cycle}: vivant — queue engine vide — {pending_agent} tâche(s) [agent] en attente")
            state["cycles"] = cycle
            state["last_cycle"] = now_iso()
            state["status"] = "running"
            save_state(state)
        except Exception as e:
            log(f"cycle {cycle}: ERROR {type(e).__name__}: {e} — le moteur continue")
        if deadline and time.time() >= deadline:
            state["status"] = "paused-timed"
            save_state(state)
            log(f"ENGINE EXIT — mode TIMED terminé au cycle {cycle}")
            return
        time.sleep(CYCLE_SECONDS)


if __name__ == "__main__":
    main()
