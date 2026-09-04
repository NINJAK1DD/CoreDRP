# CoreDRP/1 Error Registry — Draft 0.1

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

The numeric values in `protocol/coredrp-v1.proto` are provisional until v0.2 freezes the registry.

Fatal classes presently include:

- protocol version mismatch
- invalid handshake
- unauthorized sender
- unauthorized scope
- unknown event type
- unadvertised event type
- event validator unavailable
- sequence gap
- chain mismatch
- split log
- sender rollback
- recovery gap
- unapproved epoch
- event too large
- semantic contract mismatch
- receiver durability unavailable
- clock contract violation

Quarantinable semantic-payload errors will use profile-specific status codes and are not represented by `FatalError`.
