#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[1];src=(R/'model/CoreDRP.tla').read_text()
mutations={
 'prune':("/\\ pruned'=senderAck","/\\ pruned'=receiverDurable"),
 'ack':("/\\ senderAck'=receiverDurable","/\\ senderAck'=walTail"),
 'drain':("  /\\ transitionMode'=1 /\\ oldTailAtTransition'=walTail /\\ oldDrainedAtTransition'=TRUE\n","  /\\ transitionMode'=1 /\\ oldTailAtTransition'=walTail /\\ oldDrainedAtTransition'=FALSE\n"),
 'payout':(
  "  /\\ payoutEvidenceWitness'=(checkpointSeq>0 /\\ receiverDurable>=checkpointSeq /\\ CurrentProofs /\\ ~GapBlocksScalar /\\ ~policyReconciliationPending)\n",
  "  /\\ payoutEvidenceWitness'=FALSE\n"),
 'exceptional_gap':(
  "  /\\ gapRecorded'=TRUE /\\ gapTail'=walTail /\\ gapEpoch'=activeEpoch /\\ gapWildcard' \\in BOOLEAN /\\ gapStatus'=1\n",
  "  /\\ gapRecorded'=FALSE /\\ gapTail'=0 /\\ gapEpoch'=0 /\\ gapWildcard'=FALSE /\\ gapStatus'=0\n"),
 'epoch_policy':(
  "  /\\ checkpointSeq'=0 /\\ committedCheckpointFloor'=0\n  /\\ membershipProof'=FALSE /\\ membershipProofEpoch'=0 /\\ clockProof'=FALSE /\\ clockProofEpoch'=0\n  /\\ gapRecorded'=FALSE /\\ gapTail'=0 /\\ gapEpoch'=0 /\\ gapWildcard'=FALSE /\\ gapStatus'=0\n",
  "  /\\ checkpointSeq'=0 /\\ committedCheckpointFloor'=0\n  /\\ UNCHANGED <<membershipProof,membershipProofEpoch,clockProof,clockProofEpoch>>\n  /\\ gapRecorded'=FALSE /\\ gapTail'=0 /\\ gapEpoch'=0 /\\ gapWildcard'=FALSE /\\ gapStatus'=0\n")
}
for name,(old,new) in mutations.items():
 if src.count(old)!=1:raise SystemExit(f'{name}: expected exactly one mutation site, got {src.count(old)}')
 out=src.replace(old,new);d=R/'.build/mutations'/name;d.mkdir(parents=True,exist_ok=True);(d/'CoreDRP.tla').write_text(out)
print('CoreDRP TLA realistic mutations generated:', ', '.join(mutations))
