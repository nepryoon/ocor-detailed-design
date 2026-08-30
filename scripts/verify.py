#!/usr/bin/env python3
"""
OCOR ADD v1.1 — harness di verifica tool-backed.

Esegue i controlli meccanici richiesti dal §7 del prompt di review e stampa un
referto. NON esprime giudizi architetturali: quelli spettano al revisore.

Uso:
    python3 scripts/verify.py                 # referto leggibile
    python3 scripts/verify.py --json          # referto machine-readable
    python3 scripts/verify.py --add PATH      # ADD alternativo

Exit code: 0 se tutti i controlli meccanici passano, 1 altrimenti.

Dipendenze: jsonschema, PyYAML, rdflib (opzionale), grpcio-tools (opzionale).
    pip install jsonschema pyyaml rdflib grpcio-tools
"""
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ADD = os.path.join(ROOT, "inputs", "normative", "OCOR_Architectural_Design_Document_v1.1.md")

UNIVERSE = {"DEC": 196, "BR": 18, "FR": 174, "NFR": 93,
            "ARC": 23, "CAP": 26, "ELM": 103, "RSK": 60}
CORE_TOTAL = 693

results: list[dict] = []


def record(check: str, status: str, detail: str, data=None) -> None:
    results.append({"check": check, "status": status, "detail": detail, "data": data})
    icon = {"PASS": "PASS", "FAIL": "FAIL", "NOT_EXECUTED": "SKIP", "INFO": "INFO"}[status]
    print(f"[{icon}] {check}\n       {detail}")


# ───────────────────────── estrazione blocchi ─────────────────────────

def fenced_blocks(text: str):
    """Restituisce (lang, riga_iniziale_1based, corpo) per ogni blocco recintato."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^(~~~|```)(\w*)\s*$", lines[i])
        if m:
            fence, lang, start = m.group(1), m.group(2), i + 1
            j = i + 1
            while j < len(lines) and not re.match("^" + re.escape(fence) + r"\s*$", lines[j]):
                j += 1
            out.append((lang or "text", start + 1, "\n".join(lines[start:j])))
            i = j + 1
        else:
            i += 1
    return out


# ───────────────────────── 1. integrità ─────────────────────────

def check_digests(add_path: str) -> None:
    ctx = os.path.dirname(add_path)
    sums = os.path.join(ctx, "SHA256SUMS")
    if not os.path.exists(sums):
        record("Integrità sorgenti", "NOT_EXECUTED", "SHA256SUMS assente")
        return
    bad = []
    for line in open(sums, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(None, 1)
        name = name.strip()
        # i nomi sono relativi alla root del repo; fallback alla cartella del file
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            p = os.path.join(ctx, os.path.basename(name))
        if not os.path.exists(p):
            bad.append(f"{name}: assente")
            continue
        actual = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if actual != digest:
            bad.append(f"{name}: mismatch")
    if bad:
        record("Integrità sorgenti", "FAIL", "; ".join(bad))
    else:
        n = sum(1 for _ in open(sums, encoding="utf-8") if _.strip())
        record("Integrità sorgenti", "PASS", f"{n} file, tutti i digest coincidono")


# ───────────────────────── 2. schemi formali ─────────────────────────

def check_schemas(text: str):
    try:
        from jsonschema.validators import validator_for
        from jsonschema import Draft202012Validator  # noqa: F401
    except ImportError:
        record("JSON Schema", "NOT_EXECUTED", "jsonschema non installato — pip install jsonschema")
        return {}
    schemas, failures = {}, []
    for lang, ln, body in fenced_blocks(text):
        if lang != "json":
            continue
        try:
            doc = json.loads(body)
        except Exception as e:
            failures.append(f"riga {ln}: JSON non valido ({e})")
            continue
        if "$schema" not in doc:
            continue
        try:
            validator_for(doc).check_schema(doc)
            schemas[doc.get("$id", f"riga-{ln}")] = doc
        except Exception as e:
            failures.append(f"{doc.get('$id', ln)}: meta-validazione fallita ({e})")
    if failures:
        record("JSON Schema — parsing e meta-validazione", "FAIL", "; ".join(failures))
    else:
        record("JSON Schema — parsing e meta-validazione", "PASS",
               f"{len(schemas)} schemi Draft 2020-12 validi: " + ", ".join(sorted(schemas)))
    return schemas


def check_openapi(text: str) -> None:
    try:
        import yaml
    except ImportError:
        record("OpenAPI", "NOT_EXECUTED", "PyYAML non installato")
        return
    for lang, ln, body in fenced_blocks(text):
        if lang != "yaml" or "openapi:" not in body:
            continue
        try:
            doc = yaml.safe_load(body)
        except Exception as e:
            record("OpenAPI — parsing", "FAIL", f"riga {ln}: {e}")
            return
        refs = set(re.findall(r"\$ref: '?([^'\s,}]+)'?", body))
        missing = []
        for r in refs:
            if not r.startswith("#/"):
                continue
            cur = doc
            for part in r[2:].split("/"):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    missing.append(r)
                    break
        defined = set(doc.get("components", {}).get("schemas", {}))
        used = {r.split("/")[-1] for r in refs if r.startswith("#/components/schemas/")}
        detail = (f"OpenAPI {doc.get('openapi')} v{doc.get('info', {}).get('version')}; "
                  f"{len(doc.get('paths', {}))} path, {len(defined)} schemi, {len(refs)} $ref")
        if missing or (used - defined):
            record("OpenAPI — risoluzione $ref", "FAIL",
                   f"{detail}; non risolti: {missing}; referenziati non definiti: {sorted(used - defined)}")
        else:
            orphan = sorted(defined - used)
            record("OpenAPI — risoluzione $ref", "PASS",
                   f"{detail}; tutti i $ref risolti; schemi mai referenziati: {orphan or 'nessuno'}")
        record("OpenAPI — validazione semantica con validator ufficiale", "NOT_EXECUTED",
               "nessun validator OpenAPI 3.1 nel harness; il controllo NON è dichiarato superato")
        return
    record("OpenAPI", "NOT_EXECUTED", "nessun blocco OpenAPI trovato")


def check_proto(text: str) -> None:
    blocks = [b for lang, _, b in fenced_blocks(text) if lang == "proto"]
    if not blocks:
        record("Protobuf", "NOT_EXECUTED", "nessun blocco proto")
        return
    try:
        import grpc_tools.protoc  # noqa: F401
    except ImportError:
        record("Protobuf — compilazione", "NOT_EXECUTED",
               "grpcio-tools non installato — pip install grpcio-tools")
        return
    import grpc_tools
    inc = os.path.join(os.path.dirname(grpc_tools.__file__), "_proto")
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "registry.proto")
        open(f, "w", encoding="utf-8").write(blocks[0] + "\n")
        r = subprocess.run([sys.executable, "-m", "grpc_tools.protoc",
                            f"-I{d}", f"-I{inc}", f"--python_out={d}", f],
                           capture_output=True, text=True)
    if r.returncode == 0:
        record("Protobuf — compilazione", "PASS", "protoc compila senza errori")
    else:
        record("Protobuf — compilazione", "FAIL", r.stderr.strip()[:400])


def check_turtle(text: str) -> None:
    blocks = [b for lang, _, b in fenced_blocks(text) if lang == "turtle"]
    if not blocks:
        record("Turtle/RDF", "NOT_EXECUTED", "nessun blocco turtle")
        return
    try:
        import rdflib
    except ImportError:
        record("Turtle/RDF — parsing", "NOT_EXECUTED", "rdflib non installato")
        return
    try:
        g = rdflib.Graph()
        g.parse(data=blocks[0], format="turtle")
        record("Turtle/RDF — parsing", "PASS", f"{len(g)} triple")
    except Exception as e:
        record("Turtle/RDF — parsing", "FAIL", str(e)[:300])


# ───────── 3. il controllo che ha catturato RV-01 ─────────

def check_unsatisfiable_branches(schemas: dict) -> None:
    """
    Cerca i campi richiesti da un ramo condizionale ma non dichiarati fra le
    properties di uno schema con additionalProperties: false.
    Un campo così rende il ramo INSODDISFACIBILE: nessuna istanza può validare.
    È la classe del difetto RV-01 dichiarato in ADD §8.0.
    """
    findings = []

    def scan(node, path, closed_props):
        if not isinstance(node, dict):
            return
        if node.get("additionalProperties") is False and "properties" in node:
            closed_props = set(node["properties"])
        if isinstance(node.get("required"), list) and closed_props is not None:
            for name in node["required"]:
                if name not in closed_props:
                    findings.append((path, name))
        for k, v in node.items():
            if k in ("properties", "$defs") and isinstance(v, dict):
                for kk, vv in v.items():
                    scan(vv, f"{path}.{k}.{kk}", None)
            elif k in ("allOf", "anyOf", "oneOf") and isinstance(v, list):
                for n, vv in enumerate(v):
                    scan(vv, f"{path}.{k}[{n}]", closed_props)
            elif k in ("if", "then", "else", "items", "contains", "not"):
                scan(v, f"{path}.{k}", closed_props)

    for sid, doc in schemas.items():
        root = set(doc.get("properties", {})) if doc.get("additionalProperties") is False else None
        for k, v in doc.items():
            if k in ("allOf", "anyOf", "oneOf") and isinstance(v, list):
                for n, vv in enumerate(v):
                    scan(vv, f"{sid}.{k}[{n}]", root)
        for pn, pv in doc.get("properties", {}).items():
            if isinstance(pv, dict) and pv.get("additionalProperties") is False:
                sub = set(pv.get("properties", {}))
                for k, v in pv.items():
                    if k in ("allOf", "anyOf", "oneOf") and isinstance(v, list):
                        for n, vv in enumerate(v):
                            scan(vv, f"{sid}.{pn}.{k}[{n}]", sub)

    if findings:
        detail = "; ".join(f"{p} richiede '{n}' non dichiarato" for p, n in findings)
        record("Rami condizionali insoddisfacibili (classe RV-01)", "FAIL", detail, findings)
    else:
        record("Rami condizionali insoddisfacibili (classe RV-01)", "PASS",
               "nessun campo richiesto da un condizionale risulta non dichiarato")


def count_conditional_branches(schemas: dict) -> None:
    """Conta i rami condizionali per schema: il revisore DEVE coprirli con casi positivi."""
    rows = []
    for sid, doc in schemas.items():
        n = len(json.dumps(doc).split('"if"')) - 1
        rows.append((sid, n))
    detail = "; ".join(f"{s.split(':')[-2] if ':' in s else s}={n}" for s, n in rows)
    record("Rami condizionali da coprire con casi POSITIVI", "INFO",
           f"il §7.1 del prompt richiede almeno un caso positivo per ramo — {detail}", rows)


# ───────────────────────── 4. FSM ─────────────────────────

def check_fsm(text: str) -> None:
    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if "stateDiagram-v2" in l]
    if not idx:
        record("FSM", "NOT_EXECUTED", "diagramma di stato non trovato")
        return
    si = idx[0]
    j = si + 1
    while j < len(lines) and not re.match(r"^```\s*$", lines[j]):
        j += 1
    sd = "\n".join(lines[si:j])
    edges = re.findall(r"([A-Z_\[\]\*]+)\s*-->\s*([A-Z_\[\]\*]+)", sd)
    dia = {s for e in edges for s in e} - {"[*]"}

    ti = [i for i, l in enumerate(lines) if l.startswith("| `ACT-T01`")]
    if not ti:
        record("FSM — bijezione", "NOT_EXECUTED", "tabella delle transizioni non trovata")
        return
    te = ti[0]
    while te < len(lines) and lines[te].startswith("|"):
        te += 1
    tbl = "\n".join(lines[ti[0]:te])
    noise = {"G-CONTRACT", "G-AUTHORITY", "G-APPROVAL", "G-DECISION", "G-FRESHNESS",
             "G-DISPATCH", "IDEMPOTENCY_CONFLICT", "CONFIRMED", "FAILED", "NOT",
             "EXTERNAL_ADAPTER", "CANONICAL_COMMIT"}
    tst = set(re.findall(r"`([A-Z][A-Z_]{3,})`", tbl)) - noise

    only_d, only_t = sorted(dia - tst), sorted(tst - dia)
    if only_d or only_t:
        record("FSM — bijezione diagramma/tabella", "FAIL",
               f"solo nel diagramma: {only_d or 'nessuno'}; solo in tabella: {only_t or 'nessuno'}")
    else:
        record("FSM — bijezione diagramma/tabella", "PASS", f"{len(dia & tst)} stati in corrispondenza")

    nums = sorted({int(re.match(r"\d+", x).group())
                   for x in set(re.findall(r"ACT-T(\d+[a-c]?)", text))})
    if nums and nums == list(range(1, max(nums) + 1)):
        record("FSM — famiglia ACT-T", "PASS", f"ACT-T01–T{max(nums):02d} contigui, più le varianti a/b/c")
    else:
        gaps = sorted(set(range(1, max(nums) + 1)) - set(nums)) if nums else []
        record("FSM — famiglia ACT-T", "FAIL", f"identificativi mancanti: {gaps}")

    out = collections.defaultdict(list)
    for a, b in edges:
        out[a].append(b)
    nonterm = [s for s in ("EXECUTION_UNKNOWN", "COMPENSATION_UNKNOWN") if not out.get(s)]
    stuck = [s for s in dia if s not in out and s not in
             ("DENIED", "INVALIDATED", "CANCELLED", "APPROVAL_REJECTED", "APPROVAL_EXPIRED",
              "DECISION_REJECTED", "COMPENSATED", "COMPENSATION_FAILED", "OUTCOME_ASSESSED",
              "OUTCOME_UNOBSERVED", "EXECUTION_INDETERMINATE", "COMPENSATION_INDETERMINATE")]
    record("FSM — stati terminali", "INFO",
           f"stati senza archi uscenti non attesi: {stuck or 'nessuno'}; "
           f"stati di indeterminatezza privi di uscita: {nonterm or 'nessuno'}")


# ───────────────────────── 5. tracciabilità ─────────────────────────

RANGE = re.compile(r"\b(DEC|BR|FR|NFR|ARC|CAP|ELM|RSK)-(\d{1,4})\s*[–—-]\s*"
                   r"(?:(?:DEC|BR|FR|NFR|ARC|CAP|ELM|RSK)-)?(\d{1,4})\b")
SINGLE = re.compile(r"\b(DEC|BR|FR|NFR|ARC|CAP|ELM|RSK)-(\d{1,4})\b")


def expand(text: str):
    f = collections.defaultdict(set)
    for m in RANGE.finditer(text):
        p, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        if b > a and b - a <= 60:
            f[p] |= set(range(a, b + 1))
    for m in SINGLE.finditer(text):
        f[m.group(1)].add(int(m.group(2)))
    return f


def check_traceability(text: str) -> None:
    lines = text.split("\n")
    hdr = [i for i, l in enumerate(lines) if l.startswith("| Subsystem ADD |")]
    if not hdr:
        record("Tracciabilità §7", "NOT_EXECUTED", "matrice §7 non trovata")
        return
    se = hdr[0]
    while se < len(lines) and lines[se].startswith("|"):
        se += 1
    s7 = expand("\n".join(lines[hdr[0]:se]))
    rows, gaps = [], []
    for p, n in UNIVERSE.items():
        u = set(range(1, n + 1))
        got = s7[p] & u
        rows.append((p, len(got), n, sorted(u - got)))
        if p == "CAP" and (u - got) == {26}:
            continue  # CAP-026 è fuori perimetro per progetto
        if p == "DEC":
            continue  # i gate di processo non sono allocabili; verifica manuale
        if u - got:
            gaps.append(f"{p}: mancano {sorted(u - got)}")
    detail = "; ".join(f"{p} {g}/{n}" for p, g, n, _ in rows)
    record("Tracciabilità — allocazione in §7", "FAIL" if gaps else "PASS",
           detail + ("  |  GAP: " + "; ".join(gaps) if gaps else ""), rows)
    record("Universo normativo", "PASS" if sum(UNIVERSE.values()) == CORE_TOTAL else "FAIL",
           f"{sum(UNIVERSE.values())} = {CORE_TOTAL} atteso")


def check_cross_refs(text: str) -> None:
    real = set(re.findall(r"^#+ (\d+(?:\.\d+)*)", text, re.M))
    refs = set(re.findall(r"§(\d+(?:\.\d+)*)", text))
    bad = sorted(r for r in refs if r not in real)
    record("Rimandi di sezione", "FAIL" if bad else "PASS",
           f"{len(refs)} rimandi distinti, {len(real)} sezioni; non risolti: {bad or 'nessuno'}")


def check_evidence_fence(text: str) -> None:
    claims = re.findall(r"(?<!non )(?<!NON )(garantisce|assicura|è dimostrat|è provat|"
                        r"parità raggiunta|conformità raggiunta)", text, re.I)
    e1 = text.count("E1=0")
    record("Evidence fence", "FAIL" if claims else "PASS",
           f"'E1=0' ricorre {e1} volte; claim probatori non supportati: {claims or 'nessuno'}")
    for tok in ("DEC-197",):
        occ = [l for l in text.split("\n") if tok in l]
        assigned = [l for l in occ if "non assegna" not in l and "Nessun identificativo" not in l
                    and "_Draft_" not in l]
        record(f"Nessun {tok} assegnato", "FAIL" if assigned else "PASS",
               f"{len(occ)} occorrenze, tutte in forma negativa o come nome di file"
               if not assigned else f"assegnazione sospetta: {assigned[:1]}")


# ───────────────────────── main ─────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", default=DEFAULT_ADD)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.add):
        print(f"ADD non trovato: {a.add}", file=sys.stderr)
        return 2
    text = open(a.add, encoding="utf-8").read()

    print("=" * 78)
    print("OCOR ADD — harness di verifica tool-backed")
    print(f"oggetto: {os.path.relpath(a.add, ROOT)}")
    print(f"sha256:  {hashlib.sha256(text.encode()).hexdigest()}")
    print("=" * 78)

    check_digests(a.add)
    schemas = check_schemas(text)
    check_openapi(text)
    check_proto(text)
    check_turtle(text)
    if schemas:
        check_unsatisfiable_branches(schemas)
        count_conditional_branches(schemas)
    check_fsm(text)
    check_traceability(text)
    check_cross_refs(text)
    check_evidence_fence(text)

    failed = [r for r in results if r["status"] == "FAIL"]
    skipped = [r for r in results if r["status"] == "NOT_EXECUTED"]
    print("=" * 78)
    print(f"PASS {len([r for r in results if r['status']=='PASS'])}  "
          f"FAIL {len(failed)}  NOT_EXECUTED {len(skipped)}")
    if skipped:
        print("\nControlli NON eseguiti — NON dichiararli superati nel referto:")
        for r in skipped:
            print(f"  - {r['check']}: {r['detail']}")
    print("=" * 78)

    if a.json:
        out = os.path.join(ROOT, "reports", "verify_report.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"add_sha256": hashlib.sha256(text.encode()).hexdigest(),
                   "results": results}, open(out, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        print(f"referto JSON: {os.path.relpath(out, ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
