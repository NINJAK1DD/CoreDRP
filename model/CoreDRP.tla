---- MODULE CoreDRP ----
EXTENDS Naturals, FiniteSets
CONSTANT MaxSeq, EnableUnsafe
VARIABLES walTail, receiverDurable, senderAck, pruned,
          writerHeld, activeEpoch, retiredEpochs,
          checkpointFloor, lastEventTime, lastWasCheckpoint,
          blocked, receiverObserved, pendingAdmission,
          faultPending, reentryAttempted, gapRecorded,
          gapTail, transitionMode, oldDrainedAtTransition
vars == <<walTail, receiverDurable, senderAck, pruned,
          writerHeld, activeEpoch, retiredEpochs,
          checkpointFloor, lastEventTime, lastWasCheckpoint,
          blocked, receiverObserved, pendingAdmission,
          faultPending, reentryAttempted, gapRecorded,
          gapTail, transitionMode, oldDrainedAtTransition>>

Init ==
  /\ walTail = 0 /\ receiverDurable = 0 /\ senderAck = 0 /\ pruned = 0
  /\ writerHeld = TRUE /\ activeEpoch = 1 /\ retiredEpochs = {}
  /\ checkpointFloor = 0 /\ lastEventTime = 0 /\ lastWasCheckpoint = FALSE
  /\ blocked = FALSE /\ receiverObserved = 0 /\ pendingAdmission = FALSE
  /\ faultPending = 0 /\ reentryAttempted = FALSE /\ gapRecorded = FALSE
  /\ gapTail = 0 /\ transitionMode = 0 /\ oldDrainedAtTransition = FALSE

BeginAdmission ==
  /\ writerHeld /\ ~blocked /\ faultPending = 0 /\ ~pendingAdmission /\ ~gapRecorded /\ walTail < MaxSeq
  /\ pendingAdmission' = TRUE
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

DurableAdmit ==
  /\ pendingAdmission /\ writerHeld /\ ~blocked /\ faultPending = 0 /\ ~gapRecorded /\ walTail < MaxSeq
  /\ walTail' = walTail + 1
  /\ lastEventTime' = lastEventTime + 1
  /\ lastEventTime' > checkpointFloor
  /\ lastWasCheckpoint' = FALSE
  /\ pendingAdmission' = FALSE
  /\ UNCHANGED <<receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,blocked,receiverObserved,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

Checkpoint ==
  /\ writerHeld /\ ~blocked /\ faultPending = 0 /\ ~pendingAdmission /\ ~gapRecorded /\ walTail < MaxSeq
  /\ walTail' = walTail + 1
  /\ lastEventTime' = lastEventTime + 1
  /\ checkpointFloor' = lastEventTime'
  /\ lastWasCheckpoint' = TRUE
  /\ UNCHANGED <<receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,blocked,receiverObserved,pendingAdmission,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

Commit ==
  /\ ~blocked /\ faultPending = 0 /\ receiverDurable < walTail
  /\ receiverDurable' = receiverDurable + 1 /\ receiverObserved' = receiverDurable'
  /\ UNCHANGED <<walTail,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,pendingAdmission,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

RememberAck ==
  /\ ~blocked /\ faultPending = 0 /\ senderAck < receiverDurable
  /\ senderAck' = receiverDurable
  /\ UNCHANGED <<walTail,receiverDurable,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,pendingAdmission,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

Prune ==
  /\ ~blocked /\ faultPending = 0 /\ pruned < senderAck
  /\ pruned' = senderAck
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,pendingAdmission,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

Crash ==
  /\ writerHeld
  /\ writerHeld' = FALSE
  /\ pendingAdmission' = FALSE
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

AcquireWriter ==
  /\ ~writerHeld /\ ~blocked /\ faultPending = 0
  /\ writerHeld' = TRUE
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,pendingAdmission,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

ReceiverRollbackFault ==
  /\ ~blocked /\ faultPending = 0 /\ senderAck > 0
  /\ receiverObserved' = senderAck - 1
  /\ faultPending' = 1
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,pendingAdmission,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

SplitHistoryFault ==
  /\ ~blocked /\ faultPending = 0 /\ receiverDurable > 0
  /\ faultPending' = 2
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,pendingAdmission,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

DetectFault ==
  /\ faultPending # 0 /\ ~blocked
  /\ blocked' = TRUE
  /\ faultPending' = 0
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,receiverObserved,pendingAdmission,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

RecordGap ==
  /\ writerHeld /\ ~blocked /\ faultPending = 0 /\ ~pendingAdmission /\ ~gapRecorded /\ senderAck < walTail
  /\ gapRecorded' = TRUE
  /\ gapTail' = walTail
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,pendingAdmission,faultPending,reentryAttempted,transitionMode,oldDrainedAtTransition>>

NormalEpochTransition ==
  /\ writerHeld /\ ~blocked /\ faultPending = 0 /\ ~pendingAdmission
  /\ activeEpoch = 1 /\ senderAck = receiverDurable /\ receiverDurable = walTail
  /\ activeEpoch' = 2 /\ retiredEpochs' = retiredEpochs \cup {1}
  /\ transitionMode' = 1 /\ oldDrainedAtTransition' = TRUE
  /\ walTail' = 0 /\ receiverDurable' = 0 /\ senderAck' = 0 /\ pruned' = 0 /\ receiverObserved' = 0
  /\ gapRecorded' = FALSE /\ gapTail' = 0
  /\ UNCHANGED <<writerHeld,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,pendingAdmission,faultPending,reentryAttempted>>

ExceptionalEpochTransition ==
  /\ writerHeld /\ ~blocked /\ faultPending = 0 /\ ~pendingAdmission
  /\ activeEpoch = 1 /\ senderAck = receiverDurable /\ senderAck < walTail /\ gapRecorded /\ gapTail = walTail
  /\ activeEpoch' = 2 /\ retiredEpochs' = retiredEpochs \cup {1}
  /\ transitionMode' = 2 /\ oldDrainedAtTransition' = FALSE
  /\ walTail' = 0 /\ receiverDurable' = 0 /\ senderAck' = 0 /\ pruned' = 0 /\ receiverObserved' = 0
  /\ UNCHANGED <<writerHeld,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,pendingAdmission,faultPending,reentryAttempted,gapRecorded,gapTail>>

AttemptRetiredReentry ==
  /\ 1 \in retiredEpochs /\ activeEpoch = 2 /\ ~reentryAttempted
  /\ reentryAttempted' = TRUE
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,pendingAdmission,faultPending,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

UnsafePrune ==
  /\ EnableUnsafe /\ senderAck < MaxSeq
  /\ pruned' = senderAck + 1
  /\ UNCHANGED <<walTail,receiverDurable,senderAck,writerHeld,activeEpoch,retiredEpochs,checkpointFloor,lastEventTime,lastWasCheckpoint,blocked,receiverObserved,pendingAdmission,faultPending,reentryAttempted,gapRecorded,gapTail,transitionMode,oldDrainedAtTransition>>

Next == BeginAdmission \/ DurableAdmit \/ Checkpoint \/ Commit \/ RememberAck \/ Prune \/ Crash \/ AcquireWriter \/ ReceiverRollbackFault \/ SplitHistoryFault \/ DetectFault \/ RecordGap \/ NormalEpochTransition \/ ExceptionalEpochTransition \/ AttemptRetiredReentry \/ UnsafePrune

TypeOK ==
  /\ walTail \in 0..MaxSeq /\ receiverDurable \in 0..MaxSeq /\ senderAck \in 0..MaxSeq /\ pruned \in 0..MaxSeq
  /\ writerHeld \in BOOLEAN /\ activeEpoch \in {1,2} /\ retiredEpochs \subseteq {1,2}
  /\ checkpointFloor \in Nat /\ lastEventTime \in Nat /\ lastWasCheckpoint \in BOOLEAN
  /\ blocked \in BOOLEAN /\ receiverObserved \in 0..MaxSeq /\ pendingAdmission \in BOOLEAN
  /\ faultPending \in {0,1,2} /\ reentryAttempted \in BOOLEAN /\ gapRecorded \in BOOLEAN /\ gapTail \in 0..MaxSeq
  /\ transitionMode \in {0,1,2} /\ oldDrainedAtTransition \in BOOLEAN

AckSafe == senderAck <= receiverDurable
PruneSafe == pruned <= senderAck
ReceiverNotAhead == receiverDurable <= walTail
RetiredNeverCurrent == activeEpoch \notin retiredEpochs
CheckpointStrictness == lastWasCheckpoint \/ lastEventTime > checkpointFloor \/ checkpointFloor = 0
ReentryRefused == reentryAttempted => activeEpoch = 2
NormalTransitionDrained == transitionMode = 1 => oldDrainedAtTransition
ExceptionalTransitionHasGap == transitionMode = 2 => gapRecorded /\ gapTail > 0
GapFreezesAdmission == gapRecorded => ~ENABLED BeginAdmission /\ ~ENABLED Checkpoint
FaultPendingStopsProgress == faultPending # 0 => ~ENABLED BeginAdmission /\ ~ENABLED Commit /\ ~ENABLED RememberAck /\ ~ENABLED Prune

Spec == Init /\ [][Next]_vars
====
