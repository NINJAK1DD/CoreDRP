---- MODULE CoreDRP ----
EXTENDS Naturals, FiniteSets
CONSTANT MaxSeq
VARIABLES walTail, anchorTail, receiverDurable, senderAck, pruned,
          writerCount, activeEpoch, retiredEpochs,
          checkpointFloor, checkpointSeq, committedCheckpointFloor,
          temporalFloor, lastEventTime,
          membershipProof, membershipProofEpoch, clockProof, clockProofEpoch,
          gapRecorded, gapTail, gapEpoch, gapWildcard, gapStatus,
          policyGeneration, policyReconciliationPending,
          transitionMode, oldTailAtTransition, oldDrainedAtTransition,
          payoutSafeThrough, safePruneThrough, payoutEvidenceWitness,
          receiverObserved, faultPending, blocked
vars == <<walTail,anchorTail,receiverDurable,senderAck,pruned,
          writerCount,activeEpoch,retiredEpochs,
          checkpointFloor,checkpointSeq,committedCheckpointFloor,
          temporalFloor,lastEventTime,
          membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,
          gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,
          policyGeneration,policyReconciliationPending,
          transitionMode,oldTailAtTransition,oldDrainedAtTransition,
          payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,
          receiverObserved,faultPending,blocked>>

Max3(a,b,c) == IF a>=b THEN IF a>=c THEN a ELSE c ELSE IF b>=c THEN b ELSE c
CurrentProofs == membershipProof /\ membershipProofEpoch=activeEpoch /\ clockProof /\ clockProofEpoch=activeEpoch
GapBlocksScalar == gapStatus=1 \/ gapStatus=3

Init ==
  /\ walTail=0 /\ anchorTail=0 /\ receiverDurable=0 /\ senderAck=0 /\ pruned=0
  /\ writerCount=1 /\ activeEpoch=1 /\ retiredEpochs={}
  /\ checkpointFloor=0 /\ checkpointSeq=0 /\ committedCheckpointFloor=0
  /\ temporalFloor=0 /\ lastEventTime=0
  /\ membershipProof=FALSE /\ membershipProofEpoch=0 /\ clockProof=FALSE /\ clockProofEpoch=0
  /\ gapRecorded=FALSE /\ gapTail=0 /\ gapEpoch=0 /\ gapWildcard=FALSE /\ gapStatus=0
  /\ policyGeneration=1 /\ policyReconciliationPending=FALSE
  /\ transitionMode=0 /\ oldTailAtTransition=0 /\ oldDrainedAtTransition=FALSE
  /\ payoutSafeThrough=0 /\ safePruneThrough=0 /\ payoutEvidenceWitness=FALSE
  /\ receiverObserved=0 /\ faultPending=0 /\ blocked=FALSE

GapFreezesCurrentEpoch == gapRecorded /\ gapEpoch=activeEpoch /\ gapStatus=1

Admit ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ walTail<MaxSeq
  /\ walTail'=walTail+1 /\ lastEventTime'=lastEventTime+1
  /\ lastEventTime'>checkpointFloor /\ lastEventTime'>=temporalFloor
  /\ UNCHANGED <<anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Checkpoint ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ walTail<MaxSeq
  /\ walTail'=walTail+1 /\ lastEventTime'=lastEventTime+1
  /\ checkpointFloor'=lastEventTime' /\ checkpointSeq'=walTail'
  /\ UNCHANGED <<anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,committedCheckpointFloor,temporalFloor,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

PersistAnchor ==
  /\ anchorTail<walTail /\ anchorTail'=walTail
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Commit ==
  /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ receiverDurable<walTail
  /\ receiverDurable'=receiverDurable+1 /\ receiverObserved'=receiverDurable'
  /\ committedCheckpointFloor'=IF checkpointSeq>0 /\ receiverDurable'>=checkpointSeq THEN checkpointFloor ELSE committedCheckpointFloor
  /\ UNCHANGED <<walTail,anchorTail,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,faultPending,blocked>>

RememberAck ==
  /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ senderAck<receiverDurable
  /\ senderAck'=receiverDurable
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Prune ==
  /\ pruned<senderAck /\ pruned'=senderAck
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

EstablishMembershipProof ==
  /\ ~membershipProof
  /\ membershipProof'=TRUE /\ membershipProofEpoch'=activeEpoch
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

EstablishClockProof ==
  /\ ~clockProof
  /\ clockProof'=TRUE /\ clockProofEpoch'=activeEpoch
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

FuturePolicyChange ==
  /\ ~policyReconciliationPending /\ policyGeneration<MaxSeq
  /\ policyGeneration'=policyGeneration+1
  /\ membershipProof'=FALSE /\ membershipProofEpoch'=0
  /\ clockProof'=FALSE /\ clockProofEpoch'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

BeginPolicyReconciliation ==
  /\ ~policyReconciliationPending
  /\ policyReconciliationPending'=TRUE
  /\ membershipProof'=FALSE /\ membershipProofEpoch'=0
  /\ clockProof'=FALSE /\ clockProofEpoch'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

ResolvePolicyReconciliation ==
  /\ policyReconciliationPending /\ ~GapBlocksScalar /\ CurrentProofs
  /\ policyReconciliationPending'=FALSE
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

NormalEpochTransition ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~gapRecorded /\ activeEpoch=1
  /\ senderAck=receiverDurable /\ receiverDurable=walTail
  /\ transitionMode'=1 /\ oldTailAtTransition'=walTail /\ oldDrainedAtTransition'=TRUE
  /\ activeEpoch'=2 /\ retiredEpochs'=retiredEpochs \cup {1}
  /\ temporalFloor'=Max3(temporalFloor,lastEventTime,checkpointFloor)
  /\ walTail'=0 /\ anchorTail'=0 /\ receiverDurable'=0 /\ senderAck'=0 /\ pruned'=0 /\ receiverObserved'=0
  /\ checkpointSeq'=0 /\ committedCheckpointFloor'=0
  /\ membershipProof'=FALSE /\ membershipProofEpoch'=0 /\ clockProof'=FALSE /\ clockProofEpoch'=0
  /\ gapRecorded'=FALSE /\ gapTail'=0 /\ gapEpoch'=0 /\ gapWildcard'=FALSE /\ gapStatus'=0
  /\ UNCHANGED <<writerCount,checkpointFloor,lastEventTime,policyGeneration,policyReconciliationPending,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,faultPending,blocked>>

ExceptionalEpochTransition ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ activeEpoch=1
  /\ senderAck=receiverDurable /\ senderAck<walTail
  /\ transitionMode'=2 /\ oldTailAtTransition'=walTail /\ oldDrainedAtTransition'=FALSE
  /\ gapRecorded'=TRUE /\ gapTail'=walTail /\ gapEpoch'=activeEpoch /\ gapWildcard' \in BOOLEAN /\ gapStatus'=1
  /\ activeEpoch'=2 /\ retiredEpochs'=retiredEpochs \cup {1}
  /\ temporalFloor'=Max3(temporalFloor,lastEventTime,checkpointFloor)
  /\ walTail'=0 /\ anchorTail'=0 /\ receiverDurable'=0 /\ senderAck'=0 /\ pruned'=0 /\ receiverObserved'=0
  /\ checkpointSeq'=0 /\ committedCheckpointFloor'=0
  /\ membershipProof'=FALSE /\ membershipProofEpoch'=0 /\ clockProof'=FALSE /\ clockProofEpoch'=0
  /\ UNCHANGED <<writerCount,checkpointFloor,lastEventTime,policyGeneration,policyReconciliationPending,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,faultPending,blocked>>

ReconcileGap ==
  /\ gapRecorded /\ gapStatus=1
  /\ gapStatus'=2
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

WaiveGap ==
  /\ gapRecorded /\ gapStatus=1
  /\ gapStatus'=3
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

AdvancePayoutSafe ==
  /\ payoutSafeThrough<committedCheckpointFloor /\ checkpointSeq>0 /\ receiverDurable>=checkpointSeq
  /\ CurrentProofs /\ ~GapBlocksScalar /\ ~policyReconciliationPending
  /\ payoutSafeThrough'=payoutSafeThrough+1
  /\ payoutEvidenceWitness'=(checkpointSeq>0 /\ receiverDurable>=checkpointSeq /\ CurrentProofs /\ ~GapBlocksScalar /\ ~policyReconciliationPending)
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,safePruneThrough,receiverObserved,faultPending,blocked>>

AdvanceSafePrune ==
  /\ safePruneThrough<payoutSafeThrough /\ safePruneThrough'=safePruneThrough+1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Crash ==
  /\ writerCount=1 /\ writerCount'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

AcquireWriter ==
  /\ writerCount=0 /\ ~blocked /\ writerCount'=1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

ReceiverRollbackFault ==
  /\ faultPending=0 /\ senderAck>0
  /\ receiverObserved'=senderAck-1 /\ faultPending'=1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,blocked>>

DetectFault ==
  /\ faultPending#0 /\ blocked'=TRUE /\ faultPending'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,membershipProofEpoch,clockProof,clockProofEpoch,gapRecorded,gapTail,gapEpoch,gapWildcard,gapStatus,policyGeneration,policyReconciliationPending,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved>>

Next == Admit \/ Checkpoint \/ PersistAnchor \/ Commit \/ RememberAck \/ Prune \/ EstablishMembershipProof \/ EstablishClockProof \/ FuturePolicyChange \/ BeginPolicyReconciliation \/ ResolvePolicyReconciliation \/ NormalEpochTransition \/ ExceptionalEpochTransition \/ ReconcileGap \/ WaiveGap \/ AdvancePayoutSafe \/ AdvanceSafePrune \/ Crash \/ AcquireWriter \/ ReceiverRollbackFault \/ DetectFault

TypeOK ==
  /\ walTail \in 0..MaxSeq /\ anchorTail \in 0..MaxSeq /\ receiverDurable \in 0..MaxSeq /\ senderAck \in 0..MaxSeq /\ pruned \in 0..MaxSeq
  /\ writerCount \in 0..1 /\ activeEpoch \in {1,2} /\ retiredEpochs \subseteq {1,2}
  /\ checkpointFloor \in Nat /\ checkpointSeq \in 0..MaxSeq /\ committedCheckpointFloor \in Nat /\ temporalFloor \in Nat /\ lastEventTime \in Nat
  /\ membershipProof \in BOOLEAN /\ membershipProofEpoch \in {0,1,2} /\ clockProof \in BOOLEAN /\ clockProofEpoch \in {0,1,2}
  /\ gapRecorded \in BOOLEAN /\ gapTail \in 0..MaxSeq /\ gapEpoch \in {0,1,2} /\ gapWildcard \in BOOLEAN /\ gapStatus \in {0,1,2,3}
  /\ policyGeneration \in 1..MaxSeq /\ policyReconciliationPending \in BOOLEAN
  /\ transitionMode \in {0,1,2} /\ oldTailAtTransition \in 0..MaxSeq /\ oldDrainedAtTransition \in BOOLEAN
  /\ payoutSafeThrough \in Nat /\ safePruneThrough \in Nat /\ payoutEvidenceWitness \in BOOLEAN
  /\ receiverObserved \in 0..MaxSeq /\ faultPending \in {0,1} /\ blocked \in BOOLEAN

AckSafe == senderAck<=receiverDurable
PruneSafe == pruned<=senderAck
ReceiverNotAhead == receiverDurable<=walTail
AnchorNotAhead == anchorTail<=walTail
SingleWriter == writerCount<=1
RetiredNeverCurrent == activeEpoch \notin retiredEpochs
NormalTransitionDrained == transitionMode=1 => oldDrainedAtTransition
ExceptionalTransitionCovered == transitionMode=2 => gapRecorded /\ gapEpoch=1 /\ gapTail=oldTailAtTransition /\ oldTailAtTransition>0 /\ gapStatus#0
TemporalFloorSafe == lastEventTime>=checkpointFloor /\ lastEventTime>=temporalFloor
CommittedCheckpointSafe == committedCheckpointFloor<=checkpointFloor
SafePruneBound == safePruneThrough<=payoutSafeThrough
PayoutEvidenceSafe == payoutSafeThrough=0 \/ payoutEvidenceWitness
RollbackObserved == receiverObserved<senderAck => (faultPending#0 \/ blocked)
EpochProofResetSafe == (membershipProof => membershipProofEpoch=activeEpoch) /\ (clockProof => clockProofEpoch=activeEpoch)
WaivedGapBlocksScalar == gapStatus=3 => ~ENABLED AdvancePayoutSafe
PolicyReconciliationBlocksScalar == policyReconciliationPending => ~ENABLED AdvancePayoutSafe

Spec == Init /\ [][Next]_vars
====
