#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[1];src=(R/'model/CoreDRP.tla').read_text()
mutations={
 'prune':("/\\ pruned'=senderAck","/\\ pruned'=receiverDurable"),
 'ack':("/\\ senderAck'=receiverDurable","/\\ senderAck'=walTail"),
 'drain':("  /\\ transitionMode'=1 /\\ oldTailAtTransition'=walTail /\\ oldDrainedAtTransition'=TRUE\n","  /\\ transitionMode'=1 /\\ oldTailAtTransition'=walTail /\\ oldDrainedAtTransition'=FALSE\n"),
 'payout':("  /\\ payoutSafeThrough<committedCheckpointFloor /\\ checkpointSeq>0 /\\ receiverDurable>=checkpointSeq /\\ membershipProof /\\ clockProof /\\ ~gapRecorded\n", "  /\\ payoutSafeThrough<committedCheckpointFloor\n"),
 'exceptional_gap':("  /\\ gapRecorded'=TRUE /\\ gapTail'=walTail /\\ gapEpoch'=activeEpoch /\\ gapWildcard' \\in BOOLEAN\n", "  /\\ gapRecorded'=FALSE /\\ gapTail'=0 /\\ gapEpoch'=0 /\\ gapWildcard'=FALSE\n")
}
for name,(old,new) in mutations.items():
 if src.count(old)!=1:raise SystemExit(f'{name}: expected exactly one mutation site, got {src.count(old)}')
 out=src.replace(old,new);d=R/'.build/mutations'/name;d.mkdir(parents=True,exist_ok=True);(d/'CoreDRP.tla').write_text(out)
print('CoreDRP TLA realistic mutations generated:', ', '.join(mutations))
