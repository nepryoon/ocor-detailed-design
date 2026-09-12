/**
 * Phase 3 (CC-OCOR-DELIVERY-COMPLETION mandate, docs/development_methodology/
 * OCOR_LANGUAGE_POLICY.md §3, component 1) cross-language canonicalization
 * benchmark oracle.
 *
 * This is a *timing* CLI, distinct from cli/canonicalize.ts (the NFR-022
 * conformance oracle, whose exact stdout contract is asserted byte-for-byte
 * by ocor-runtime/tests/sdk/test_typescript_sdk_conformance.py and must not
 * change). It reads one I-JSON document per stdin line, times `repeats`
 * back-to-back canonicalizeJson()+canonicalSha256() calls per document with
 * process.hrtime.bigint() (excluding I/O and JSON.parse), and reports the
 * median per-call duration for that document in nanoseconds -- the same
 * "median over repeated calls on the same document" statistic
 * scripts/run_language_migration_benchmark.py computes on the Python side,
 * so the two engines are compared on identical work, not on subprocess or
 * I/O overhead.
 */

import * as readline from "node:readline";
import { canonicalizeJson, canonicalSha256, type IJsonValue } from "../canonical.js";

const REPEATS = Number(process.argv[2] ?? "20");

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const a = sorted[mid];
  if (a === undefined) {
    throw new Error("median() called on an empty array");
  }
  if (sorted.length % 2 !== 0) {
    return a;
  }
  const b = sorted[mid - 1];
  if (b === undefined) {
    throw new Error("median() index out of range");
  }
  return (a + b) / 2;
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });

rl.on("line", (line: string) => {
  const value = JSON.parse(line) as IJsonValue;
  const durationsNs: number[] = [];
  for (let i = 0; i < REPEATS; i += 1) {
    const start = process.hrtime.bigint();
    const text = canonicalizeJson(value);
    canonicalSha256(value);
    const end = process.hrtime.bigint();
    durationsNs.push(Number(end - start));
    if (text.length === 0) {
      throw new Error("unreachable: canonicalizeJson produced an empty string");
    }
  }
  process.stdout.write(JSON.stringify({ median_ns: median(durationsNs) }) + "\n");
});
