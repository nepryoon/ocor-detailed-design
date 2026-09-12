/**
 * Typed, fail-closed exceptions for the OCOR client boundary.
 *
 * Mirrors the stable `code` strings of ocor-runtime/src/ocor_runtime/errors.py
 * for the subset of the error taxonomy a client-side SDK can raise or must
 * recognize by code alone (NFR-022 error-model identity). This file is
 * hand-written kernel support code, not a generated contract -- the same
 * distinction the Python runtime draws between its hand-written canonical.py
 * and the generator-produced ocor_contracts.py.
 */

export abstract class OCORError extends Error {
  abstract readonly code: string;

  constructor(message: string) {
    super(message);
    this.name = new.target.name;
  }
}

export class CanonicalizationError extends OCORError {
  readonly code: string = "CANONICALIZATION_INVALID";
}

export class DigestProviderError extends CanonicalizationError {
  override readonly code: string = "DIGEST_PROVIDER_FAILURE";
}
