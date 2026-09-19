# Miningcore schema fixture

`miningcore-createdb.sql` is an unmodified copy of
[`src/Miningcore/Persistence/Postgres/Scripts/createdb.sql`](https://github.com/NINJAK1DD/miningcore/blob/2702579ca7281509572dbf722fbffcf306c99aed/src/Miningcore/Persistence/Postgres/Scripts/createdb.sql)
at revision `2702579ca7281509572dbf722fbffcf306c99aed`.

SHA-256: `b39bc84e790c61dfc4d6bfdeefeedc2287a5cd6fb47dfde5c0f09c02bcc035ec`.
The adjacent `miningcore-LICENSE` preserves its upstream MIT licence.

Tests validate these exact bytes, then omit only `SET ROLE miningcore;` while
installing this schema in the disposable CoreDRP CI database. The accounting rows
are synthetic, separately inserted database records. Tests do not claim to have
run a live Miningcore instance, miner, daemon or production payout.
