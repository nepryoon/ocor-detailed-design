# OCOR Compensating Protection Mode

## Disposition

GitHub reports `main.protected=false`. The private repository's current plan returns
HTTP 403 for rulesets and classic branch protection. The paid capability therefore
remains `EXTERNAL_CONTROL_PENDING`; the controls below are not server-side equivalent.

## Enforced controls

- autonomous dispatch rejects dirty worktrees, detached HEAD, `main`, unrecognised
  coordinator branches and a starting commit different from `origin/main`;
- task work occurs only on the exact `task/OCOR-DEV-NNNN-<slug>` branch generated from
  current `main`, after accepted hard dependencies;
- push, PR and expected-HEAD merge are an atomic runner requirement; direct automated
  push to `main` and force push are absent from the runner and rejected by the optional
  repository-local pre-push hook;
- both observed mandatory CI contexts must be green immediately before merge;
- the runner uses `--match-head-commit`, fetches the resulting `main`, verifies that it
  contains the exact PR HEAD and rechecks the immutable `inputs/` tree digest;
- evidence JSON, raw output and gate manifest are content-addressed before integration;
- `.github/CODEOWNERS` remains documentation only because the current plan cannot
  enforce it server-side.

## Residual risk

An administrator or human client can still push directly to `main` outside this
automation. Enabling GitHub Pro (or making the repository public, which is not
authorized here) and applying `reports/planning/OCOR_MAIN_PROTECTION_REQUEST.json` is
the exact external action required to replace this residual platform risk.
