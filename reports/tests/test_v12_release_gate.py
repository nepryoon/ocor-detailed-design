#!/usr/bin/env python3
"""Gate documentale finale e mapping patch→Amendment Log per v1.2 Candidate."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md"
PATCH = ROOT / "reports/OCOR_ADD_v1.1_to_v1.2.patch"
RESULTS = Path(__file__).with_name("v12_release_gate_results.json")
text = CANDIDATE.read_text(encoding="utf-8")
patch_text = PATCH.read_text(encoding="utf-8")
records: list[dict] = []


def add(check: str, passed: bool, detail: object) -> None:
    records.append({"check": check, "pass": bool(passed), "detail": detail})


baseline = ROOT / "inputs/normative/OCOR_Architectural_Design_Document_v1.1.md"
digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
add("digest baseline v1.1", digest == "3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f", digest)

# Tutte le sorgenti elencate nei manifest devono essere byte-identiche.
for manifest in (ROOT / "inputs/normative/SHA256SUMS", ROOT / "inputs/supporting/prior/SHA256SUMS.prior"):
    if not manifest.exists():
        add(f"manifest presente {manifest.relative_to(ROOT)}", False, "missing")
        continue
    mismatches = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = relative.lstrip("* ")
        target = ROOT / relative
        actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else "MISSING"
        if actual != expected:
            mismatches.append({"file": relative, "expected": expected, "actual": actual})
    add(f"integrità {manifest.relative_to(ROOT)}", not mismatches, mismatches or "all entries match")

changed_protected = subprocess.run(
    ["git", "diff", "--name-only", "--", "inputs", "prompts", "docs/detailed_design"],
    cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
add("nessuna modifica a sorgenti protette", not changed_protected, changed_protected)

# Mapping di ogni hunk al primo heading che precede la nuova riga e quindi a un emendamento.
headings = []
for number, line in enumerate(text.splitlines(), 1):
    match = re.match(r"^(#{1,6})\s+(.+)$", line)
    if match:
        top = "0"
        section = re.search(r"(?:^|\s)([1-8])(?:\.|\s|$)", match.group(2))
        if section:
            top = section.group(1)
        headings.append((number, top, match.group(2)))

coverage = {
    "0": "V12-AM-01", "1": "V12-AM-02", "2": "V12-AM-14",
    "3": "V12-AM-02", "4": "V12-AM-04", "5": "V12-AM-05",
    "6": "V12-AM-12", "7": "V12-AM-13", "8": "V12-AM-15",
}
hunks = []
for index, match in enumerate(re.finditer(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@", patch_text, re.M), 1):
    new_line = int(match.group(1))
    prior = [h for h in headings if h[0] <= max(new_line, 1)]
    heading = prior[-1] if prior else (0, "0", "front matter")
    amendment = coverage.get(heading[1])
    present = amendment is not None and f"`{amendment}`" in text
    hunks.append({"hunk": index, "new_line": new_line, "section": heading[1],
                  "heading": heading[2], "amendment": amendment, "mapped": present})
add("ogni hunk mappato all'Amendment Log", bool(hunks) and all(h["mapped"] for h in hunks), hunks)

# Reference integrity per rimandi numerici; locator storici v1.0 non sono destinazioni correnti.
defined = set()
for line in text.splitlines():
    match = re.match(r"^#{1,6}\s+((?:[1-8])(?:\.\d+)*)\b", line)
    if match:
        defined.add(match.group(1))
refs = set(re.findall(r"§\s*([1-8](?:\.\d+)*)", text))
unresolved = sorted(ref for ref in refs if ref not in defined and not ref.startswith("8.0"))
add("rimandi di sezione risolti", not unresolved, unresolved)

# Dialect/brand isolation nei soli blocchi di contratto pubblici.
blocks = re.findall(r"(?:```|~~~)(json|yaml|proto|turtle)\n(.*?)\n(?:```|~~~)", text, re.S)
forbidden = re.compile(r"\b(TypeQL|WOQL|SPARQL|Datalog|Cypher|SQL|TypeDB|TerminusDB|TDB2)\b", re.I)
dialect_hits = [{"lang": lang, "token": m.group(0)} for lang, body in blocks for m in forbidden.finditer(body)]
add("nessun dialect/backend nei contratti pubblici", not dialect_hits, dialect_hits)

# Unicità degli identificativi definiti nella candidata.
schema_ids = re.findall(r'"\$id"\s*:\s*"([^"]+)"', text)
transition_rows = re.findall(r"^\| `(ACT-T\d+[a-z]?)` \|", text, re.M)
amendment_rows = re.findall(r"^\| `(V12-AM-\d+)` \|", text, re.M)
duplicates = {
    "schema_ids": sorted({x for x in schema_ids if schema_ids.count(x) > 1}),
    "transition_ids": sorted({x for x in transition_rows if transition_rows.count(x) > 1}),
    "amendment_ids": sorted({x for x in amendment_rows if amendment_rows.count(x) > 1}),
}
add("identificativi definiti univoci", not any(duplicates.values()), duplicates)

# Evidence fence e authority fence.
unsupported_claims = re.findall(
    r"(?<!non )(?<!NON )(garantisce|assicura|è dimostrat[oa]|è provat[oa]|parità raggiunta|conformità raggiunta)",
    text, re.I)
add("evidence fence", "E1=0" in text and "E2=0" in text and not unsupported_claims,
    {"E1=0": text.count("E1=0"), "E2=0": text.count("E2=0"), "claims": unsupported_claims})
add("zero promozioni Verified", "zero requisiti `Verified`" in text or "requisiti `Verified` restano `0`" in text,
    "document control and §7.3")
add("stato candidato", "PROPOSED — AWAITING CHANGE CONTROL" in text and "Candidate" in text, "explicit")

# Scope invariants richiesti.
scope_checks = {
    "ELM-070_deferred": "`ELM-070` differita" in text,
    "FR-095_change_control": "`FR-095`" in text and "P0/MVP" in text and "AWAITING CHANGE CONTROL" in text,
    "NFR-078_not_deferred": "`NFR-078` è P0/MVP e non `Differito`" in text,
    "CAP-026_out": "`CAP-026` — Complete Foundry/AIP/Apollo breadth" in text,
}
add("scope fence", all(scope_checks.values()), scope_checks)

summary = {
    "source": str(CANDIDATE.relative_to(ROOT)),
    "patch": str(PATCH.relative_to(ROOT)),
    "hunks": len(hunks),
    "total": len(records),
    "passed": sum(item["pass"] for item in records),
    "failed": sum(not item["pass"] for item in records),
    "records": records,
}
RESULTS.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for item in records:
    print("PASS" if item["pass"] else "FAIL", "—", item["check"])
print(f"TOTAL {summary['total']} PASS {summary['passed']} FAIL {summary['failed']} HUNKS {summary['hunks']}")
print(f"RESULTS {RESULTS.relative_to(ROOT)}")
sys.exit(1 if summary["failed"] else 0)
