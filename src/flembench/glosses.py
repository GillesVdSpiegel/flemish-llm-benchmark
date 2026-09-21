"""Draft glosses (short meanings) for lexicon candidates, from two independent LLMs.

The author chose LLM-drafted glosses to keep curation fast. To keep that honest:
- drafts are shown to the author during curation, who accepts or overrides each one, and the
  decision records where the final gloss came from (`gloss_source`);
- two models from different providers draft independently (Claude writes directly into
  glosses.csv; Gemini gets the words without Claude's glosses), and disagreements are flagged;
- a model writes "?" instead of guessing.

Files (committed; words and glosses only):
    data/curation/glosses.csv                        one row per candidate
    data/curation/gloss_prompt/PROMPT.md             prompt for the second model
    data/curation/gloss_prompt/batches/NN.txt        id|BE|word lines
    data/curation/gloss_prompt/results/<model>__NN.txt   raw output: id|gloss lines
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from flembench.paths import CURATION_DIR

GLOSSES_FILE = CURATION_DIR / "glosses.csv"
PROMPT_DIR = CURATION_DIR / "gloss_prompt"
FIELDS = [
    "variety", "word", "claude_gloss", "claude_confidence", "gemini_gloss", "gemini_model",
    "agreement",
]  # fmt: skip
UNKNOWN = {"", "?"}

PROMPT = """\
Below is a list of Dutch words. Each line has an id, the country where the word is typically
used (BE = Belgium/Flanders, NL = the Netherlands) and the word.

For each word, give its meaning AS USED IN THAT COUNTRY, as a short gloss in standard Dutch
(1 to 6 words), the way a dictionary would.

Rules:
- If you are not sure what the word means in that country, write ? . Do not guess.
- If the word has several meanings, give the most common one in that country first and
  separate meanings with a semicolon.
- Output exactly one line per input line, in the same order, in the form id|gloss
- Output nothing else: no header, no explanation, no code fences.

Words:
"""


def load(path: Path = GLOSSES_FILE) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {
            (r["variety"], r["word"]): {k: r.get(k, "") for k in FIELDS} for r in csv.DictReader(f)
        }


def save(glosses: dict[tuple[str, str], dict], path: Path = GLOSSES_FILE) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n", restval="")
        w.writeheader()
        for key in sorted(glosses):
            w.writerow(glosses[key])
    tmp.replace(path)


def export(
    words: list[tuple[str, str, str]], batch_size: int = 200, root: Path = PROMPT_DIR
) -> list[Path]:
    """words: (id, variety, word) in the prefilter's shuffled order."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "PROMPT.md").write_text(PROMPT, encoding="utf-8", newline="\n")
    batch_dir = root / "batches"
    batch_dir.mkdir(exist_ok=True)
    paths = []
    for n, start in enumerate(range(0, len(words), batch_size), start=1):
        p = batch_dir / f"{n:02d}.txt"
        chunk = words[start : start + batch_size]
        p.write_text(
            "".join(f"{i}|{v.upper()}|{w}\n" for i, v, w in chunk), encoding="utf-8", newline="\n"
        )
        paths.append(p)
    return paths


_LINE = re.compile(r"^\s*(w\d{4})\s*\|\s*(.*?)\s*$")


def parse_output(text: str) -> tuple[dict[str, str], list[str]]:
    out, problems = {}, []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("```"):
            continue
        m = _LINE.match(line)
        if not m:
            problems.append(f"unparseable line: {line.strip()[:60]!r}")
            continue
        out[m[1]] = "" if m[2] in UNKNOWN else m[2]
    return out, problems


def import_results(
    glosses: dict[tuple[str, str], dict],
    id_map: dict[str, tuple[str, str]],
    root: Path = PROMPT_DIR,
) -> tuple[dict[tuple[str, str], dict], dict]:
    """Fill gemini_gloss from results/<model>__NN.txt. id_map: id -> (variety, word)."""
    glosses = {k: dict(v) for k, v in glosses.items()}
    problems, filled, models = [], 0, set()
    for p in sorted((root / "results").glob("*.txt")):
        model = p.stem.split("__")[0]
        models.add(model)
        parsed, probs = parse_output(p.read_text(encoding="utf-8"))
        problems += [f"{p.name}: {x}" for x in probs]
        for wid, gloss in parsed.items():
            key = id_map.get(wid)
            if key is None or key not in glosses:
                problems.append(f"{p.name}: unknown id {wid}")
                continue
            glosses[key]["gemini_gloss"] = gloss or "?"
            glosses[key]["gemini_model"] = model
            filled += 1
    return glosses, {"models": sorted(models), "filled": filled, "problems": problems}


def draft_for(row: dict | None) -> tuple[str, str]:
    """(gloss to pre-fill, its source). Claude first; Gemini if Claude did not know."""
    if not row:
        return "", ""
    if row.get("claude_gloss"):
        return row["claude_gloss"], "claude-opus-5"
    gem = row.get("gemini_gloss", "")
    if gem and gem != "?":
        return gem, row.get("gemini_model") or "gemini"
    return "", ""
