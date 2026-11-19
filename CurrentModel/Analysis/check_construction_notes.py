#!/usr/bin/env python3
"""Keep CurrentModel/CONSTRUCTION-NOTES.md honest about the generator.

Run from the repo root (or anywhere; paths are resolved from this file):

    python3 CurrentModel/Analysis/check_construction_notes.py

It checks four things and exits 1, printing what is stale, if any of them fail:

1. every generator name the notes cite in backticks still exists:
     `foo()` or `foo`      -> a function/variable in airship_slice.py
     `NAME` (ALL CAPS)     -> a constant or environment variable in the generator,
                             or in make_fcstd.py / make_pieces.py / fcstd_doc.py /
                             check_outputs.py (the scripts the notes also cite)
     --flag                -> an argument of check_outputs.py
2. every file path cited in backticks exists in the repo (scratch paths under a
   build/ folder are reported but not required: they are git-ignored probes);
3. the INDEX at the top lists every section with the line range it really has;
4. every OpenAirShips task that has a notes file in the fleet task folder has an
   entry in section 10, the LESSONS LOG.

A cited line number ("`skin_ribs` 599") is not required to be exact: the checker
warns when the real def is more than 40 lines away, and does not fail on it.

Backticks mean "this is a name or a path". Prose words in backticks are listed in
PROSE below; anything else in backticks is checked.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))            # the repo root
NOTES = os.path.join(ROOT, "CurrentModel", "CONSTRUCTION-NOTES.md")
SLICE_DIR = os.path.join(ROOT, "CurrentModel", "CAD Files", "SimplifiedSlice")
GEN = os.path.join(SLICE_DIR, "airship_slice.py")
OTHERS = [os.path.join(SLICE_DIR, "make_fcstd.py"),
          os.path.join(SLICE_DIR, "make_pieces.py"),
          os.path.join(ROOT, "CurrentModel", "CAD Files", "fcstd_doc.py"),
          os.path.join(ROOT, "CurrentModel", "Analysis", "check_outputs.py")]
CHECKER = OTHERS[-1]
TASKS_DIR = "/home/rhy/strata-fleet/tasks"

# backticked words that are prose or parameters, not generator names
PROSE = {"depth", "envelope", "inset", "off", "psi", "theta", "freecadcmd"}
# checker flags that are not check_outputs.py arguments
FLAG_OK = {"--pass"}
# path extensions the notes may cite
EXTS = (".py", ".md", ".stl", ".step", ".json", ".sh", ".FCStd", ".txt")
SEARCH_DIRS = [ROOT, os.path.join(ROOT, "CurrentModel"), SLICE_DIR,
               os.path.join(ROOT, "CurrentModel", "Analysis"),
               os.path.join(ROOT, "CurrentModel", "CAD Files"),
               os.path.join(ROOT, "CurrentModel", "CAD Files", "Propulsion", "print"),
               os.path.join(ROOT, "CurrentModel", "Print Files")]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def defined(name, src):
    """Is NAME assigned on the left-hand side of some line (tuple-aware)?"""
    for line in src.splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        lhs = line.split("=", 1)[0]
        if re.search(rf"(^|[,\s]){re.escape(name)}(?=\s*(?:,|$))", lhs):
            return True
    return False


def resolve_path(cite):
    """Find a cited path: as given from the repo root, then by name in the known
    folders, then by a bounded walk of CurrentModel."""
    if os.path.exists(os.path.join(ROOT, cite)):
        return os.path.join(ROOT, cite)
    base = os.path.basename(cite.rstrip("/"))
    for d in SEARCH_DIRS:
        p = os.path.join(d, base)
        if os.path.exists(p):
            return p
    for d in SEARCH_DIRS:
        for dirpath, _dirs, files in os.walk(d):
            if base in files:
                return os.path.join(dirpath, base)
    return None


def main():
    if not os.path.exists(NOTES):
        print(f"FAIL  no manual at {os.path.relpath(NOTES, ROOT)}")
        return 1
    text = read(NOTES)
    lines = text.splitlines()
    gen = read(GEN)
    others = {p: read(p) for p in OTHERS if os.path.exists(p)}
    problems, warns, scratch = [], [], []

    # ---- 1. cited names -----------------------------------------------------
    cites = set(re.findall(r"`([^`\n]+)`", text))
    for cite in sorted(cites):
        c = cite.strip()
        if any(ch in c for ch in "<>*|") or c == "":
            continue                       # a placeholder or a shell fragment
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\(\)", c)
        if m:
            name = m.group(1)
            if not re.search(rf"(^|\s)(def|class)\s+{name}\b", gen) and not defined(name, gen):
                problems.append(f"generator name {cite}() is gone from airship_slice.py")
            continue
        if re.fullmatch(r"[a-z_][a-z0-9_]*", c):
            if c in PROSE:
                continue
            if (not re.search(rf"(^|\s)(def|class)\s+{c}\b", gen) and not defined(c, gen)
                    and f'"{c}"' not in gen and f"'{c}'" not in gen):
                problems.append(f"generator name {cite} is gone from airship_slice.py"
                                " (no def, no assignment, no such string)")
            else:
                at = re.search(rf"^def\s+{c}\(", gen, re.M)
                if at:
                    line = gen[:at.start()].count("\n") + 1
                    near = re.search(rf"`{re.escape(c)}`\s+(\d{{2,4}})\b", text)
                    if near and abs(int(near.group(1)) - line) > 40:
                        warns.append(f"{cite} is now at line {line}, the notes say {near.group(1)}")
            continue
        if re.fullmatch(r"_?[A-Z][A-Z0-9_]*", c):
            if defined(c, gen):
                continue
            where = [os.path.basename(p) for p, src in others.items() if defined(c, src)
                     or f'"{c}"' in src]
            if where:
                continue
            if f'"{c}"' in gen or f"'{c}'" in gen:      # an environment variable
                continue
            problems.append(f"constant {cite} is not defined in airship_slice.py"
                            f" (nor in {', '.join(os.path.basename(p) for p in others)})")
            continue
        if c.startswith("--"):
            flag = c.split()[0]
            if flag in FLAG_OK:
                continue
            if f'"{flag}"' not in others.get(CHECKER, "") and f"'{flag}'" not in others.get(CHECKER, ""):
                problems.append(f"checker flag {flag} is not an argument of check_outputs.py")
            continue
        if "/" in c or c.endswith(EXTS):
            if os.path.basename(c.rstrip("/")).endswith(EXTS) or c.endswith("/"):
                if re.search(r"(^|/)build/", c):
                    scratch.append(c)        # a git-ignored probe: noted, not required
                    continue
                if resolve_path(c) is None:
                    problems.append(f"cited path {cite} does not exist")
            continue
        # anything else (a sentence, a formula, a checker output line) is prose
    # ---- 2. the INDEX and the section line ranges ---------------------------
    heads = [(i + 1, int(m.group(1)), m.group(2).strip())
             for i, line in enumerate(lines)
             if (m := re.match(r"^## (\d+) (.+)$", line))]
    if not heads:
        problems.append("the manual has no '## N SECTION' headings")
    index = {}
    for i, line in enumerate(lines):
        m = re.match(r"^- (\d+) ([^:]+): (\d+)-(\d+)\s*$", line)
        if m:
            index[int(m.group(1))] = (m.group(2).strip(), int(m.group(3)), int(m.group(4)), i + 1)
    for ln, n, title in heads:
        end = next((l2 - 1 for l2, _, _ in heads if l2 > ln), len(lines))
        if n not in index:
            problems.append(f"section {n} {title!r} is missing from the INDEX")
            continue
        ititle, lo, hi, _il = index[n]
        if ititle != title:
            problems.append(f"INDEX calls section {n} {ititle!r}, the heading says {title!r}")
        if (lo, hi) != (ln, end):
            problems.append(f"INDEX line range for section {n} {title} is {lo}-{hi},"
                            f" it is really {ln}-{end}")
    for n in index:
        if n not in {h[1] for h in heads}:
            problems.append(f"INDEX lists section {n}, which has no heading")

    # ---- 3. every task with notes has a LESSONS LOG entry -------------------
    log = ""
    for i, line in enumerate(lines):
        if re.match(r"^## 10 ", line):
            log = "\n".join(lines[i:])
            break
    if not log:
        problems.append("there is no section 10 LESSONS LOG")
    elif os.path.isdir(TASKS_DIR):
        ids = sorted({m.group(1) for f in os.listdir(TASKS_DIR)
                      if (m := re.match(r"notes-(f\d+)-openairships.*\.md$", f))})
        missing = [t for t in ids if t not in log]
        if missing:
            problems.append("LESSONS LOG has no entry for: " + " ".join(missing))
        print(f"notes files: {len(ids)} OpenAirShips tasks; "
              f"{len(ids) - len(missing)} have a LESSONS LOG entry")
    else:
        warns.append(f"no task folder at {TASKS_DIR}: task-id coverage not checked")

    for w in warns:
        print(f"warn   {w}")
    for s in scratch:
        print(f"scratch {s} (git-ignored probe, not required)")
    if problems:
        for p in problems:
            print(f"STALE  {p}")
        print(f"{len(problems)} thing(s) in CONSTRUCTION-NOTES.md no longer match the repo")
        return 1
    print(f"CONSTRUCTION-NOTES.md: {len(lines)} lines, {len(heads)} sections, "
          f"{len(cites)} citations checked, all current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
