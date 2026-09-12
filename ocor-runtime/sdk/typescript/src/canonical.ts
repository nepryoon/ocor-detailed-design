/**
 * RFC 8785 (JCS) JSON canonicalization.
 *
 * Ports ocor-runtime/src/ocor_runtime/canonical.py to TypeScript. Unlike the
 * Python port -- which has to hand-replicate ECMAScript's Number::toString
 * algorithm and UTF-16 code-unit string ordering, because Python's own JSON
 * and string defaults differ from both -- this implementation runs on the
 * ECMAScript engine JCS actually specifies, so `String(number)` and the
 * default string comparison operators already ARE the required algorithms.
 * No independent digit-manipulation logic is re-derived here; this is
 * intentional; it is the reason this port is expected to be correct rather
 * than merely tested, and mirrors DEC-166/REM-0007's use of Node.js as the
 * oracle for the Python implementation's own boundary values.
 */

import { createHash } from "node:crypto";
import { CanonicalizationError, DigestProviderError } from "./errors.js";

export const MAX_SAFE_INTEGER = 9_007_199_254_740_991;

export type IJsonValue =
  | null
  | boolean
  | number
  | string
  | readonly IJsonValue[]
  | { readonly [key: string]: IJsonValue };

function hasLoneSurrogate(value: string): boolean {
  for (const codeUnit of value) {
    const codepoint = codeUnit.codePointAt(0);
    if (codepoint !== undefined && codepoint >= 0xd800 && codepoint <= 0xdfff && codeUnit.length === 1) {
      return true;
    }
  }
  return false;
}

function serializeString(value: string): string {
  if (hasLoneSurrogate(value)) {
    throw new CanonicalizationError("lone UTF-16 surrogate is not valid I-JSON");
  }
  let encoded = '"';
  for (const character of value) {
    switch (character) {
      case '"':
        encoded += '\\"';
        break;
      case "\\":
        encoded += "\\\\";
        break;
      case "\b":
        encoded += "\\b";
        break;
      case "\t":
        encoded += "\\t";
        break;
      case "\n":
        encoded += "\\n";
        break;
      case "\f":
        encoded += "\\f";
        break;
      case "\r":
        encoded += "\\r";
        break;
      default: {
        const codepoint = character.codePointAt(0) ?? 0;
        encoded += codepoint <= 0x1f ? `\\u${codepoint.toString(16).padStart(4, "0")}` : character;
      }
    }
  }
  return encoded + '"';
}

function serializeNumber(value: number): string {
  if (!Number.isFinite(value)) {
    throw new CanonicalizationError("NaN and Infinity are not valid I-JSON numbers");
  }
  if (Object.is(value, -0) || value === 0) {
    return "0";
  }
  // Unlike the Python port, there is no separate integer path: JavaScript
  // has one `number` type, already binary64, so an integer outside
  // MAX_SAFE_INTEGER is exactly the same value the finiteness check above
  // already accepted -- no extra representability check is needed.
  // ECMAScript's Number::toString is exactly the JCS-mandated algorithm:
  // shortest round-tripping decimal, scientific notation for
  // exponent >= 21 or <= -7, lowercase "e" with an explicit "+" on the
  // positive exponent. `String(value)` already produces this.
  return String(value);
}

function utf16LessThan(a: string, b: string): boolean {
  // Default `<` on strings already compares by UTF-16 code unit sequence,
  // which is exactly the JCS key-ordering requirement -- no manual encoding
  // to utf-16-be is needed the way the Python port requires.
  return a < b;
}

function isPlainObject(value: unknown): value is { readonly [key: string]: IJsonValue } {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function serialize(value: IJsonValue): string {
  if (value === null) {
    return "null";
  }
  if (value === true) {
    return "true";
  }
  if (value === false) {
    return "false";
  }
  if (typeof value === "string") {
    return serializeString(value);
  }
  if (typeof value === "number") {
    return serializeNumber(value);
  }
  if (Array.isArray(value)) {
    return "[" + value.map((item: IJsonValue) => serialize(item)).join(",") + "]";
  }
  if (isPlainObject(value)) {
    const keys = Object.keys(value);
    for (const key of keys) {
      if (hasLoneSurrogate(key)) {
        throw new CanonicalizationError("lone UTF-16 surrogate is not valid I-JSON");
      }
    }
    keys.sort((a, b) => (utf16LessThan(a, b) ? -1 : utf16LessThan(b, a) ? 1 : 0));
    const entries = keys.map((key) => `${serializeString(key)}:${serialize(value[key] as IJsonValue)}`);
    return "{" + entries.join(",") + "}";
  }
  throw new CanonicalizationError(`value of type ${typeof value} is not an I-JSON value`);
}

/** Return the RFC 8785 canonical JSON text for a parsed JSON value. */
export function canonicalizeJson(value: IJsonValue): string {
  return serialize(value);
}

/** Return RFC 8785 canonical JSON encoded as UTF-8 bytes. */
export function canonicalize(value: IJsonValue): Uint8Array {
  return new TextEncoder().encode(canonicalizeJson(value));
}

/** Return a lowercase SHA-256 digest over canonical UTF-8 JSON. */
export function canonicalSha256(value: IJsonValue): string {
  // canonicalize() runs outside the try so a CanonicalizationError (an
  // invalid input) propagates as itself instead of being mislabeled as a
  // digest-provider failure -- only the hash computation itself is guarded,
  // matching the Python port's `except OSError` (not `except Exception`).
  const bytes = canonicalize(value);
  try {
    return createHash("sha256").update(bytes).digest("hex");
  } catch {
    throw new DigestProviderError("SHA-256 provider failure");
  }
}
