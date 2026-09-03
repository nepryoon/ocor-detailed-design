# OCOR model operating profile

## Effective session fingerprint — 2026-09-02

| Field | Observed value |
|---|---|
| Model identity | `NOT_EXPOSED_BY_RUNTIME` — no model name is asserted |
| Reasoning effort | `NOT_EXPOSED_BY_RUNTIME` |
| Codex CLI | `0.152.1` |
| Git | `2.55.0` |
| Python | `3.14.7` |
| Docker | `29.7.2` |
| uv | `NOT_AVAILABLE_LOCAL` |
| Host | Linux x86_64, kernel `7.2.2-1-cachyos` |

La CLI verificata supporta `--model` e profili, ma non è stata verificata una chiave
repository-specific per il reasoning effort; pertanto non viene creato alcun file di
configurazione con chiavi ipotizzate. Un launch profile può usare soltanto un nome
modello confermato dall'ambiente di avvio e la sintassi documentata da `codex --help`.

Routing: medium per modifiche bounded e deterministicamente verificate; high per
architettura, concorrenza, causalità, security e recovery; xhigh o massimo disponibile
per protocol design, gate closure e final review. Se non selezionabile, compensare con
task più piccoli, reference model, oracle deterministici, property/mutation test,
clean-room rerun e verifier fresh-context.

Ogni critical change separa implementer e verifier. Il verifier riceve soltanto fonti
normative, diff ed evidenza; identità/configurazione e finding sono registrati.
