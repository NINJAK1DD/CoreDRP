---- MODULE CoreDRP ----
EXTENDS Naturals, FiniteSets
CONSTANT MaxSeq
VARIABLES walTail, anchorTail, receiverDurable, senderAck, pruned,
          writerCount, activeEpoch, retiredEpochs,
          checkpointFloor, checkpointSeq, committedCheckpointFloor,
          temporalFloor, lastEventTime,
          membershipProof, clockProof,
          gapRecorded, gapTail, gapEpoch, gapWildcard,
          transitionMode, oldTailAtTransition, oldDrainedAtTransition,
          payoutSafeThrough, safePruneThrough, payoutEvidenceWitness,
          receiverObserved, faultPending, blocked
vars == <<walTail,anchorTail,receiverDurable,senderAck,pruned,
          writerCount,activeEpoch,retiredEpochs,
          checkpointFloor,checkpointSeq,committedCheckpointFloor,
          temporalFloor,lastEventTime,membershipProof,clockProof,
          gapRecorded,gapTail,gapEpoch,gapWildcard,
          transitionMode,oldTailAtTransition,oldDrainedAtTransition,
          payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,
          receiverObserved,faultPending,blocked>>

Max3(a,b,c) == IF a>=b THEN IF a>=c THEN a ELSE c ELSE IF b>=c THEN b ELSE c

Init ==
  /\ walTail=0 /\ anchorTail=0 /\ receiverDurable=0 /\ senderAck=0 /\ pruned=0
  /\ writerCount=1 /\ activeEpoch=1 /\ retiredEpochs={}
  /\ checkpointFloor=0 /\ checkpointSeq=0 /\ committedCheckpointFloor=0
  /\ temporalFloor=0 /\ lastEventTime=0
  /\ membershipProof=FALSE /\ clockProof=FALSE
  /\ gapRecorded=FALSE /\ gapTail=0 /\ gapEpoch=0 /\ gapWildcard=FALSE
  /\ transitionMode=0 /\ oldTailAtTransition=0 /\ oldDrainedAtTransition=FALSE
  /\ payoutSafeThrough=0 /\ safePruneThrough=0 /\ payoutEvidenceWitness=FALSE
  /\ receiverObserved=0 /\ faultPending=0 /\ blocked=FALSE

GapFreezesCurrentEpoch == gapRecorded /\ gapEpoch=activeEpoch

Admit ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ walTail<MaxSeq
  /\ walTail'=walTail+1
  /\ lastEventTime'=lastEventTime+1
  /\ lastEventTime'>checkpointFloor /\ lastEventTime'>=temporalFloor
  /\ UNCHANGED <<anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Checkpoint ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ walTail<MaxSeq
  /\ walTail'=walTail+1
  /\ lastEventTime'=lastEventTime+1
  /\ checkpointFloor'=lastEventTime'
  /\ checkpointSeq'=walTail'
  /\ UNCHANGED <<anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,committedCheckpointFloor,temporalFloor,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

PersistAnchor ==
  /\ anchorTail<walTail
  /\ anchorTail'=walTail
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Commit ==
  /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ receiverDurable<walTail
  /\ receiverDurable'=receiverDurable+1 /\ receiverObserved'=receiverDurable'
  /\ committedCheckpointFloor'=IF checkpointSeq>0 /\ receiverDurable'>=checkpointSeq THEN checkpointFloor ELSE committedCheckpointFloor
  /\ UNCHANGED <<walTail,anchorTail,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,faultPending,blocked>>

RememberAck ==
  /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ senderAck<receiverDurable
  /\ senderAck'=receiverDurable
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Prune ==
  /\ pruned<senderAck
  /\ pruned'=senderAck
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

EstablishMembershipProof ==
  /\ ~membershipProof
  /\ membershipProof'=TRUE
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

EstablishClockProof ==
  /\ ~clockProof
  /\ clockProof'=TRUE
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

RecordGap ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~gapRecorded /\ senderAck<walTail
  /\ gapRecorded'=TRUE /\ gapTail'=walTail /\ gapEpoch'=activeEpoch
  /\ gapWildcard' \in BOOLEAN
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

NormalEpochTransition ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~gapRecorded /\ activeEpoch=1
  /\ senderAck=receiverDurable /\ receiverDurable=walTail
  /\ transitionMode'=1
  /\ oldTailAtTransition'=walTail
  /\ oldDrainedAtTransition'=(senderAck=receiverDurable /\ receiverDurable=walTail)
  /\ activeEpoch'=2 /\ retiredEpochs'=retiredEpochs \cup {1}
  /\ temporalFloor'=Max3(temporalFloor,lastEventTime,checkpointFloor)
  /\ walTail'=0 /\ anchorTail'=0 /\ receiverDurable'=0 /\ senderAck'=0 /\ pruned'=0 /\ receiverObserved'=0
  /\ checkpointSeq'=0 /\ committedCheckpointFloor'=0
  /\ gapRecorded'=FALSE /\ gapTail'=0 /\ gapEpoch'=0 /\ gapWildcard'=FALSE
  /\ UNCHANGED <<writerCount,checkpointFloor,lastEventTime,membershipProof,clockProof,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,faultPending,blocked>>

ExceptionalEpochTransition ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ activeEpoch=1
  /\ senderAck=receiverDurable /\ senderAck<walTail
  /\ gapRecorded /\ gapEpoch=activeEpoch /\ gapTail=walTail
  /\ transitionMode'=2 /\ oldTailAtTransition'=walTail /\ oldDrainedAtTransition'=FALSE
  /\ activeEpoch'=2 /\ retiredEpochs'=retiredEpochs \cup {1}
  /\ temporalFloor'=Max3(temporalFloor,lastEventTime,checkpointFloor)
  /\ walTail'=0 /\ anchorTail'=0 /\ receiverDurable'=0 /\ senderAck'=0 /\ pruned'=0 /\ receiverObserved'=0
  /\ checkpointSeq'=0 /\ committedCheckpointFloor'=0
  /\ UNCHANGED <<writerCount,checkpointFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,faultPending,blocked>>

AdvancePayoutSafe ==
  /\ payoutSafeThrough<committedCheckpointFloor /\ checkpointSeq>0 /\ receiverDurable>=checkpointSeq /\ senderAck>=checkpointSeq /\ membershipProof /\ clockProof /\ ~gapRecorded
  /\ payoutSafeThrough'=payoutSafeThrough+1
  /\ payoutEvidenceWitness'=(checkpointSeq>0 /\ receiverDurable>=checkpointSeq /\ senderAck>=checkpointSeq /\ membershipProof /\ clockProof /\ ~gapRecorded)
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,safePruneThrough,receiverObserved,faultPending,blocked>>

AdvanceSafePrune ==
  /\ safePruneThrough<payoutSafeThrough
  /\ safePruneThrough'=safePruneThrough+1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

Crash ==
  /\ writerCount=1 /\ writerCount'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

AcquireWriter ==
  /\ writerCount=0 /\ ~blocked /\ writerCount'=1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved,faultPending,blocked>>

ReceiverRollbackFault ==
  /\ faultPending=0 /\ senderAck>0
  /\ receiverObserved'=senderAck-1 /\ faultPending'=1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,blocked>>

DetectFault ==
  /\ faultPending#0 /\ blocked'=TRUE /\ faultPending'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,checkpointSeq,committedCheckpointFloor,temporalFloor,lastEventTime,membershipProof,clockProof,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,payoutEvidenceWitness,receiverObserved>>

Next == Admit \/ Checkpoint \/ PersistAnchor \/ Commit \/ RememberAck \/ Prune \/ EstablishMembershipProof \/ EstablishClockProof \/ RecordGap \/ NormalEpochTransition \/ ExceptionalEpochTransition \/ AdvancePayoutSafe \/ AdvanceSafePrune \/ Crash \/ AcquireWriter \/ ReceiverRollbackFault \/ DetectFault

TypeOK ==
  /\ walTail \in 0..MaxSeq /\ anchorTail \in 0..MaxSeq /\ receiverDurable \in 0..MaxSeq /\ senderAck \in 0..MaxSeq /\ pruned \in 0..MaxSeq
  /\ writerCount \in 0..1 /\ activeEpoch \in {1,2} /\ retiredEpochs \subseteq {1,2}
  /\ checkpointFloor \in Nat /\ checkpointSeq \in 0..MaxSeq /\ committedCheckpointFloor \in Nat /\ temporalFloor \in Nat /\ lastEventTime \in Nat
  /\ membershipProof \in BOOLEAN /\ clockProof \in BOOLEAN
  /\ gapRecorded \in BOOLEAN /\ gapTail \in 0..MaxSeq /\ gapEpoch \in {0,1,2} /\ gapWildcard \in BOOLEAN
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
ExceptionalTransitionCovered == transitionMode=2 => gapRecorded /\ gapEpoch=1 /\ gapTail=oldTailAtTransition /\ oldTailAtTransition>0
TemporalFloorSafe == lastEventTime>=checkpointFloor /\ lastEventTime>=temporalFloor
CommittedCheckpointSafe == committedCheckpointFloor<=checkpointFloor
SafePruneBound == safePruneThrough<=payoutSafeThrough
PayoutEvidenceSafe == payoutSafeThrough=0 \/ payoutEvidenceWitness
RollbackObserved == receiverObserved<senderAck => (faultPending#0 \/ blocked)

Spec == Init /\ [][Next]_vars
====
