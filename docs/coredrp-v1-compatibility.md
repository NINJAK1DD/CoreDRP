# CoreDRP/1 Compatibility Registry — Draft 0.6

This registry is normative.

| Component | Supported version | Minimum dependency | Draft 0.6 endpoint support |
|---|---|---|---|
| Core | 1.1 | n/a | REQUIRED |
| Core | 1.0 | n/a | HISTORICAL / MUST NOT advertise |
| Mining profile | 1.1 | Core 1.1 | REQUIRED when Mining is used |
| Miningcore profile | 1.1 | Core 1.1 + Mining 1.1 same scope | REQUIRED when Miningcore integration is used |

Draft 0.6 implementations advertise Core maximum minor exactly 1 and are compatible only with peers that select Core 1.1. They MUST NOT advertise Core 1.0 compatibility because the Core 1.1 clock-response/state protocol cannot be represented by the current 1.1 schema under Core 1.0 semantics.

Each `ProfileSupport` row represents one exact profile version and carries that exact version's minimum Core. Selection occurs only after Core selection and chooses the highest mutually supported profile major, then highest minor in that major, among rows whose minimum Core is satisfied.

Miningcore 1.1 MUST NOT be selected unless Mining 1.1 is also selected for every Miningcore-bound scope.
