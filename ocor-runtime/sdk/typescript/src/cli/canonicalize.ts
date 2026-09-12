/**
 * NFR-022 cross-SDK conformance harness support.
 *
 * Reads one I-JSON value as a JSON-encoded string on a single line of stdin,
 * canonicalizes it with this SDK's own canonical.ts, and prints one
 * JSON-encoded result line to stdout:
 *   {"canonical": "<text>", "digest": "<hex>", "error_code": null}
 * or, on a rejected input:
 *   {"canonical": null, "digest": null, "error_code": "<stable code>"}
 *
 * This CLI is test-support tooling, not a generated contract: it exists so
 * the Python conformance suite can drive the real, compiled TypeScript
 * implementation as a subprocess and compare its output byte-for-byte
 * against the Python kernel's, exactly as Node.js is used as the REM-0007
 * oracle for Python's own RFC 8785 boundary values.
 */

import * as readline from "node:readline";
import { canonicalizeJson, canonicalSha256, type IJsonValue } from "../canonical.js";
import { OCORError } from "../errors.js";

const rl = readline.createInterface({ input: process.stdin, terminal: false });

rl.on("line", (line: string) => {
  let result: { canonical: string | null; digest: string | null; error_code: string | null };
  try {
    const value = JSON.parse(line) as IJsonValue;
    result = { canonical: canonicalizeJson(value), digest: canonicalSha256(value), error_code: null };
  } catch (error) {
    const code = error instanceof OCORError ? error.code : "UNEXPECTED_ERROR";
    result = { canonical: null, digest: null, error_code: code };
  }
  process.stdout.write(JSON.stringify(result) + "\n");
});
