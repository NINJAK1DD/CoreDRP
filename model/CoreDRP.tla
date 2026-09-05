---- MODULE CoreDRP ----
EXTENDS Naturals, FiniteSets
CONSTANT MaxSeq
VARIABLES walTail, anchorTail, receiverDurable, senderAck, pruned,
          writerCount, activeEpoch, retiredEpochs,
          checkpointFloor, temporalFloor, lastEventTime,
          gapRecorded, gapTail, gapEpoch, gapWildcard,
          transitionMode, oldTailAtTransition, oldDrainedAtTransition,
          payoutSafeThrough, safePruneThrough,
          receiverObserved, faultPending, blocked
vars == <<walTail,anchorTail,receiverDurable,senderAck,pruned,
          writerCount,activeEpoch,retiredEpochs,
          checkpointFloor,temporalFloor,lastEventTime,
          gapRecorded,gapTail,gapEpoch,gapWildcard,
          transitionMode,oldTailAtTransition,oldDrainedAtTransition,
          payoutSafeThrough,safePruneThrough,
          receiverObserved,faultPending,blocked>>

Max3(a,b,c) == IF a>=b THEN IF a>=c THEN a ELSE c ELSE IF b>=c THEN b ELSE c

Init ==
  /\ walTail=0 /\ anchorTail=0 /\ receiverDurable=0 /\ senderAck=0 /\ pruned=0
  /\ writerCount=1 /\ activeEpoch=1 /\ retiredEpochs={}
  /\ checkpointFloor=0 /\ temporalFloor=0 /\ lastEventTime=0
  /\ gapRecorded=FALSE /\ gapTail=0 /\ gapEpoch=0 /\ gapWildcard=FALSE
  /\ transitionMode=0 /\ oldTailAtTransition=0 /\ oldDrainedAtTransition=FALSE
  /\ payoutSafeThrough=0 /\ safePruneThrough=0
  /\ receiverObserved=0 /\ faultPending=0 /\ blocked=FALSE

GapFreezesCurrentEpoch == gapRecorded /\ gapEpoch=activeEpoch

Admit ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ walTail<MaxSeq
  /\ walTail'=walTail+1
  /\ lastEventTime'=lastEventTime+1
  /\ lastEventTime'>checkpointFloor /\ lastEventTime'>=temporalFloor
  /\ UNCHANGED <<anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

Checkpoint ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ walTail<MaxSeq
  /\ walTail'=walTail+1
  /\ lastEventTime'=lastEventTime+1
  /\ checkpointFloor'=lastEventTime'
  /\ UNCHANGED <<anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,temporalFloor,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

PersistAnchor ==
  /\ anchorTail<walTail
  /\ anchorTail'=walTail
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

Commit ==
  /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ receiverDurable<walTail
  /\ receiverDurable'=receiverDurable+1 /\ receiverObserved'=receiverDurable'
  /\ UNCHANGED <<walTail,anchorTail,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,faultPending,blocked>>

RememberAck ==
  /\ ~blocked /\ faultPending=0 /\ ~GapFreezesCurrentEpoch /\ senderAck<receiverDurable
  /\ senderAck'=receiverDurable
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

Prune ==
  /\ pruned<senderAck
  /\ pruned'=senderAck
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

RecordGap ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~gapRecorded /\ senderAck<walTail
  /\ gapRecorded'=TRUE /\ gapTail'=walTail /\ gapEpoch'=activeEpoch
  /\ gapWildcard' \in BOOLEAN
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

NormalEpochTransition ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ ~gapRecorded /\ activeEpoch=1
  /\ senderAck=receiverDurable /\ receiverDurable=walTail
  /\ transitionMode'=1
  /\ oldTailAtTransition'=walTail
  /\ oldDrainedAtTransition'=(senderAck=receiverDurable /\ receiverDurable=walTail)
  /\ activeEpoch'=2 /\ retiredEpochs'=retiredEpochs \cup {1}
  /\ temporalFloor'=Max3(temporalFloor,lastEventTime,checkpointFloor)
  /\ walTail'=0 /\ anchorTail'=0 /\ receiverDurable'=0 /\ senderAck'=0 /\ pruned'=0 /\ receiverObserved'=0
  /\ gapRecorded'=FALSE /\ gapTail'=0 /\ gapEpoch'=0 /\ gapWildcard'=FALSE
  /\ UNCHANGED <<writerCount,checkpointFloor,lastEventTime,payoutSafeThrough,safePruneThrough,faultPending,blocked>>

ExceptionalEpochTransition ==
  /\ writerCount=1 /\ ~blocked /\ faultPending=0 /\ activeEpoch=1
  /\ senderAck=receiverDurable /\ senderAck<walTail
  /\ gapRecorded /\ gapEpoch=activeEpoch /\ gapTail=walTail
  /\ transitionMode'=2 /\ oldTailAtTransition'=walTail /\ oldDrainedAtTransition'=FALSE
  /\ activeEpoch'=2 /\ retiredEpochs'=retiredEpochs \cup {1}
  /\ temporalFloor'=Max3(temporalFloor,lastEventTime,checkpointFloor)
  /\ walTail'=0 /\ anchorTail'=0 /\ receiverDurable'=0 /\ senderAck'=0 /\ pruned'=0 /\ receiverObserved'=0
  /\ UNCHANGED <<writerCount,checkpointFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,payoutSafeThrough,safePruneThrough,faultPending,blocked>>

AdvancePayoutSafe ==
  /\ payoutSafeThrough<checkpointFloor
  /\ payoutSafeThrough'=payoutSafeThrough+1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,safePruneThrough,receiverObserved,faultPending,blocked>>

AdvanceSafePrune ==
  /\ safePruneThrough<payoutSafeThrough
  /\ safePruneThrough'=safePruneThrough+1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,receiverObserved,faultPending,blocked>>

Crash ==
  /\ writerCount=1 /\ writerCount'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

AcquireWriter ==
  /\ writerCount=0 /\ ~blocked /\ writerCount'=1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved,faultPending,blocked>>

ReceiverRollbackFault ==
  /\ faultPending=0 /\ senderAck>0
  /\ receiverObserved'=senderAck-1 /\ faultPending'=1
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,blocked>>

DetectFault ==
  /\ faultPending#0 /\ blocked'=TRUE /\ faultPending'=0
  /\ UNCHANGED <<walTail,anchorTail,receiverDurable,senderAck,pruned,writerCount,activeEpoch,retiredEpochs,checkpointFloor,temporalFloor,lastEventTime,gapRecorded,gapTail,gapEpoch,gapWildcard,transitionMode,oldTailAtTransition,oldDrainedAtTransition,payoutSafeThrough,safePruneThrough,receiverObserved>>

Next == Admit \/ Checkpoint \/ PersistAnchor \/ Commit \/ RememberAck \/ Prune \/ RecordGap \/ NormalEpochTransition \/ ExceptionalEpochTransition \/ AdvancePayoutSafe \/ AdvanceSafePrune \/ Crash \/ AcquireWriter \/ ReceiverRollbackFault \/ DetectFault

TypeOK ==
  /\ walTail \in 0..MaxSeq /\ anchorTail \in 0..MaxSeq /\ receiverDurable \in 0..MaxSeq /\ senderAck \in 0..MaxSeq /\ pruned \in 0..MaxSeq
  /\ writerCount \in 0..1 /\ activeEpoch \in {1,2} /\ retiredEpochs \subseteq {1,2}
  /\ checkpointFloor \in Nat /\ temporalFloor \in Nat /\ lastEventTime \in Nat
  /\ gapRecorded \in BOOLEAN /\ gapTail \in 0..MaxSeq /\ gapEpoch \in {0,1,2} /\ gapWildcard \in BOOLEAN
  /\ transitionMode \in {0,1,2} /\ oldTailAtTransition \in 0..MaxSeq /\ oldDrainedAtTransition \in BOOLEAN
  /\ payoutSafeThrough \in Nat /\ safePruneThrough \in Nat /\ receiverObserved \in 0..MaxSeq /\ faultPending \in {0,1} /\ blocked \in BOOLEAN

AckSafe == senderAck<=receiverDurable
PruneSafe == pruned<=senderAck
ReceiverNotAhead == receiverDurable<=walTail
AnchorNotAhead == anchorTail<=walTail
SingleWriter == writerCount<=1
RetiredNeverCurrent == activeEpoch \notin retiredEpochs
NormalTransitionDrained == transitionMode=1 => oldDrainedAtTransition
ExceptionalTransitionCovered == transitionMode=2 => gapRecorded /\ gapEpoch=1 /\ gapTail=oldTailAtTransition /\ oldTailAtTransition>0
TemporalFloorSafe == lastEventTime>=checkpointFloor /\ lastEventTime>=temporalFloor
SafePruneBound == safePruneThrough<=payoutSafeThrough
RollbackObserved == receiverObserved<senderAck => (faultPending#0 \/ blocked)

Spec == Init /\ [][Next]_vars
====
