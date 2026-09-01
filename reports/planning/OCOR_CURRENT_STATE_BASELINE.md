# OCOR Current State Baseline

## Verdict

The documentation chain is approved at design level, but runtime conformance is `NOT_ESTABLISHED / NO-GO`. The current code is a small Python reference/compatibility slice, not the approved C1–C8 PoC topology.

At `67cda4b44a8d27b831eb461b1e28d71e1d3398ab`, immutable-input checks are 8 PASS and the document harness is 14 PASS. The complete local pytest command has 1 collection FAIL (`psycopg` missing), which prevents 5 live PostgreSQL tests from executing. The materially different non-live command has 104 PASS, 0 FAIL, 0 SKIPPED; the 5 live cases remain `NOT_EXECUTED`, never PASS.

## Capability baseline

| Capability | Required by | Status | Current implementation | Current evidence | Missing evidence | Gap | Risk |
|---|---|---|---|---|---|---|---|
| Canonical JSON/digest kernel | ADD §3.0; LLD §1.1 | `IMPLEMENTED_AND_VERIFIED` | ocor_runtime/canonical.py; EV-001..004 and BA-04 | Qualifying multi-language contract evidence | Generated SDK parity | Generated SDK parity | MEDIUM |
| C1 compiler/IR | ADD §3.1; LLD §2.1 | `PARTIALLY_IMPLEMENTED` | SemanticCompiler validates/canonicalizes one envelope | DSL, type checking, releases, diff, migration, generation | Architecture C1 exceeds current helper | Architecture C1 exceeds current helper | HIGH |
| C2 query gateway | ADD §3.3; LLD §2.2 | `ABSENT` | Current c2_identity.py is identity registry only | Named queries, purpose/policy planning, evidence, watermarks | Current module label misallocates responsibility | Current module label misallocates responsibility | CRITICAL |
| C3 asserted state | ADD §§2.3/3.6; LLD §2.3 | `PARTIALLY_IMPLEMENTED` | In-memory AtomicOutboxStore; PostgreSQL fallback and five live tests | Approved full commit bindings, qualifying backend campaign | Local live suite cannot collect without psycopg | Local live suite cannot collect without psycopg | HIGH |
| C4 projections | ADD §2.2; LLD §2.4 | `ABSENT` | Current c4_marking.py implements marking lattice only | TypeDB/Jena adapters, watermarks, rebuild, drift | No projection backend code | No projection backend code | CRITICAL |
| C5 event backbone | ADD §§2.2/3.8; LLD §2.5 | `ABSENT` | Current c5_actions.py is an obsolete 32-transition action FSM | Kafka/Strimzi, registry, replay, DLQ, quarantine | Component naming conflicts with approved allocation | Component naming conflicts with approved allocation | CRITICAL |
| C6 governed action engine | ADD §4.1; LLD §§2.6/3 | `PARTIALLY_IMPLEMENTED` | CapabilityAuthority plus action FSM/emission helpers in C5/C6/C7 labels | Exact 44 transitions, Human Gate, Decision, EMISSION-FENCE, safety | 12 transitions absent and durable effects incomplete | 12 transitions absent and durable effects incomplete | CRITICAL |
| C7 causal runtime | ADD §4.2; LLD §2.7 | `ABSENT` | Current c7_emission.py is emission fence | Scenario branches, interventions, counterfactuals, uncertainty, sealing | No causal symbols/tests | No causal symbols/tests | CRITICAL |
| C8 governed agent kernel | ADD §4.3; LLD §2.8 | `PARTIALLY_IMPLEMENTED` | Sandbox, token budget, identify/abstain model wrapper | AgentRun/Task/Assignment/Commitment/Handoff/Dissent and governed tools | No durable multi-agent orchestration | No durable multi-agent orchestration | HIGH |
| Full Governed Agent Memory | DEC-208; ADD Part II; LLD §2.8.1–2.8.8 | `ABSENT` | No runtime source, schema or test implementation | All 8 kinds, 7 scopes, lifecycle, stores, retrieval, deletion, replay, promotion | FGM-01–20 absent | FGM-01–20 absent | CRITICAL |
| Security control plane | ADD §5; LLD §4 | `DOCUMENTATION_ONLY` | In-process marking and capability primitives | OPA, Keycloak, SPIFFE/SPIRE, OpenBao, mTLS, dual control | No real control-plane integration | No real control-plane integration | CRITICAL |
| Deployment and recovery | ADD §6; LLD §5 | `ABSENT` | CI starts PostgreSQL service only | Compose, Helm, observability, backup, restore, air-gap | No deploy directory or runbooks | No deploy directory or runbooks | HIGH |
| BA-01–BA-08 | LLD §7.1 | `COMPATIBILITY_ONLY` | Files named BA exercise mostly in-memory abstractions; one live PostgreSQL slice exists | Real selected-component cases for all BA IDs | Legacy names do not establish architectural BA evidence | Legacy names do not establish architectural BA evidence | CRITICAL |
| FGM-01–FGM-20 | LLD §7.2 | `ABSENT` | Only documented future oracles | Twenty qualifying real-backend cases | Full-memory runtime remains NO-GO | Full-memory runtime remains NO-GO | CRITICAL |
| Synthetic mission thread | LLD §7.3 | `COMPATIBILITY_ONLY` | EV-035 is an in-process Python path using no C2 gateway/C4/C5/C7 causal/memory services | Real selected-service C1-C8+memory thread | Current test name cannot prove full architecture | Current test name cannot prove full architecture | CRITICAL |
| CI merge prevention | Repository workflows | `UNKNOWN` | PR workflow exists and ran green on DEC-209; branch-protection API returned HTTP 403 | Explicit G0-G7 jobs, no mandatory skip, readable/enforced protection rules | Current workflow mixes legacy runtime/document gates and enforcement cannot be proven | Current workflow mixes legacy runtime/document gates and enforcement cannot be proven | HIGH |

## Evidence interpretation

- `ocor-runtime/tests/acceptance_ev/test_ev_029_035_fence_agent_e2e.py::test_ev_035...` is in-process and does not traverse approved real C2, C4, C5, C7 or memory services; it is `COMPATIBILITY_ONLY` for the final mission thread.
- `ocor-runtime/tests/backend_assumptions/` names BA cases, but most use `AtomicOutboxStore` or fakes. They are preparatory tests, not qualifying BA-01–BA-08 selected-component evidence.
- `.github/workflows/ocor-validation-closure.yml` previously ran a live PostgreSQL job, but DEC-209 explicitly excludes legacy runtime/BA/EV steps from its evidence scope.
- No `FGM-*` runtime test files or memory implementation modules exist. Therefore Full Governed Agent Memory remains `NO-GO`.
- `gh api repos/nepryoon/ocor-detailed-design/branches/main/protection` returned HTTP 403; merge-blocking protection is `UNKNOWN`, not inferred from prior green runs.
