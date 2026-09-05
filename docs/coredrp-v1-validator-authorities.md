# CoreDRP Profile Validator Authority Registry — Draft 0.6

**Status:** normative Mining 1.1 / Miningcore 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md`. It allocates the only validator/profile authority digests that may appear in `QUARANTINE_RECONCILIATION` ADMIN field 11 under Profile 1.1.

Receiver-local authority names, source-code hashes, deployment IDs, build hashes, operator strings, or unregistered digests MUST NOT be accepted as reconciliation authority.

## 1. Canonical authority digest

`validator_profile_digest32 = SHA256(validator_authority_source)`.

The source grammar is:

`uint16_be(1)`
`|| uint16_be(authority_id_len) || authority_id_ascii`
`|| uint32_be(authority_major)`
`|| uint32_be(authority_minor)`
`|| uint16_be(event_type_count)`
`|| repeated uint16_be(event_type) sorted ascending`.

Authority ID is exact ASCII. Event types are range-checked before sorting, MUST be unique, and are the complete set this authority may revalidate. Unknown authority versions or digests are `ADMIN_ACTION_CONFLICT` and MUST NOT mutate quarantine state.

## 2. Profile 1.1 exact-revalidation authority

Authority ID:

`coredrp.profile11.exact-revalidation`

Version: `1.0`.

Event types:

- `0x0100 MiningShareEvent`;
- `0x0200 MiningcoreAccountingShareEvent`.

Canonical source hex:

`00010024636f72656472702e70726f66696c6531312e65786163742d726576616c69646174696f6e0000000100000000000201000200`

SHA-256 / allocated `validator_profile_digest32`:

`22a09b0066b1b1e7fdd6258fc435ea4e4c7ad7aff8b0440915fec452abb88e04`

### 2.1 Exact semantics

This authority exists only to correct a **validator implementation defect** while preserving the semantics and contracts that governed the immutable event.

For each payout-effect scope, reconciliation MUST:

1. load the exact Mining and, where applicable, Miningcore scope-contract digests that governed that event/effect scope;
2. apply the normative Profile 1.1 registries for those exact contract versions, including all accounting-schema/settlement-policy rules selected by those contracts;
3. derive the payout-effect scope set and missing financial effects solely from those normative rules and the immutable original payload;
4. reject reconciliation if the payload is still invalid under those exact semantics.

The authority MUST NOT reinterpret the event under a different payout scheme, different accounting schema, different settlement policy, different scope-contract digest, receiver-local exception, or future profile semantics.

If a true semantic correction or migration is required rather than an implementation bug fix, Profile 1.1 has **no authority for it**. A future profile/registry revision must allocate a new authority and, where financial interpretation changes, satisfy the profile-transition migration rules.

## 3. Allow-list rule

For Profile 1.1 the allowed reconciliation-authority set is exactly the digests allocated by this registry. At Draft 0.6 freeze it contains only:

`22a09b0066b1b1e7fdd6258fc435ea4e4c7ad7aff8b0440915fec452abb88e04`.

Implementations MUST compare ADMIN field 11 byte-for-byte with this registry before revalidation. Matching the digest identifies the normative authority algorithm; it does not by itself prove that the resulting financial effect is correct. The receiver must still execute revalidation and atomically apply the missing effects as required by `coredrp-v1-quarantine-safety.md`.

## 4. Critical candidate quarantine limitation

Profile 1.1 allocates no exact-revalidation authority or corrected-effect grammar for `0x0201` or `0x0202`. A quarantined direct candidate or candidate-state event is therefore waiver-only under this profile: a reconciliation attempt MUST return `ADMIN_ACTION_CONFLICT`, including when it supplies the allocated share authority digest. A waiver does not restore candidate validity, permit deletion of its evidence, satisfy `SettlementSafe`, or unblock a financial migration that depends on the candidate. Local consensus submission remains independent. Recovery with restored financial safety requires a future explicitly allocated authority/effect grammar and applicable migration rules; an operator flag or another candidate identity is not reconciliation.
