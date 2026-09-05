#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Regression: witness-serialized Bitcoin candidates require a BIP141 commitment."""
from __future__ import annotations
import copy
import runpy

ns = runpy.run_path('tools/verify_profile_vectors.py')
P = ns['P']
BC = ns['BC']
read_varint = ns['read_varint']
parse_tx = ns['parse_tx']
sha256d = ns['sha256d']
merkle = ns['merkle']
validate_candidate = ns['validate_candidate']

v = copy.deepcopy(P['bitcoin_direct_candidate_segwit'])
m = BC(); m.ParseFromString(bytes.fromhex(v['payload_hex']))
block = bytearray(m.serialized_block)

# Replace the 6-byte BIP141 commitment magic with a non-commitment OP_RETURN prefix
# of identical length, preserving transaction framing while removing the commitment.
magic = bytes.fromhex('6a24aa21a9ed')
replacement = bytes.fromhex('6a24aa21a9ee')
pos = block.find(magic, 80)
assert pos >= 0, 'SegWit fixture must contain a witness commitment'
block[pos:pos+len(magic)] = replacement

# Reparse the changed block, then rebuild all non-witness evidence that legitimately
# changes because the coinbase txid changed. This makes the candidate self-consistent
# except for the now-missing witness commitment.
count, tx_pos = read_varint(block, 80)
txs = []
for _ in range(count):
    tx = parse_tx(block, tx_pos)
    txs.append(tx)
    tx_pos = tx['end']
assert tx_pos == len(block)
assert any(tx['segwit'] for tx in txs)
assert not any(len(script) >= 38 and script[:6] == magic for _, script in txs[0]['outs'])

coinbase_txid_internal = sha256d(txs[0]['nonwit'])
txids = [sha256d(tx['nonwit']) for tx in txs]
block[36:68] = merkle(txids)
block_hash_display = sha256d(bytes(block[:80]))[::-1]

m.serialized_block = bytes(block)
m.coinbase_txid = coinbase_txid_internal[::-1]
m.block_hash = block_hash_display

# The mutated former commitment output is no longer consensus metadata. Account for it
# explicitly as a zero-valued direct recipient so every other candidate consistency rule
# can still pass if the witness-commitment requirement were accidentally removed.
mutated_scripts = [script for value, script in txs[0]['outs'] if value == 0 and script[:6] == replacement]
assert len(mutated_scripts) == 1
r = m.recipients.add(); r.script_pub_key = mutated_scripts[0]; r.amount_satoshis = 0

v['payload_hex'] = m.SerializeToString().hex()
assert validate_candidate(v) is False, 'witness candidate without BIP141 commitment was accepted'
print('CoreDRP missing witness commitment regression: OK')
