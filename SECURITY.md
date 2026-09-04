# Security Policy

> Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

CoreDRP/1 is currently a draft specification and is not yet recommended for production use.

For vulnerabilities in the CoreDRP specification or a CoreDRP implementation, avoid publishing exploit details in a public issue before maintainers have had an opportunity to assess the report.

During the draft stage, contact the repository owner privately through the contact information associated with the GitHub account/repository.

Security-sensitive areas include, but are not limited to:

- mTLS identity and authorization;
- hash-chain verification;
- WAL durability and recovery;
- epoch transitions;
- acknowledgement-before-durability bugs;
- quarantine/advance authorization;
- completeness-gap handling;
- payout or pruning safety;
- direct block-candidate evidence.
