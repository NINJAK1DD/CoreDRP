---- MODULE CoreDRP ----
EXTENDS Naturals, FiniteSets
CONSTANT MaxSeq, EnableUnsafe
VARIABLES walTail, receiverDurable, senderAck, pruned,
          writerHeld, activeEpoch, retiredEpochs,
          checkpointFloor, lastEventTime, blocked,
          receiverObserved
vars == <<walTail, receiverDurable, senderAck, pruned,
          writerHeld, activeEpoch, retiredEpochs,
          checkpointFloor, lastEventTime, blocked,
          receiverObserved>>

Init ==
  /\ walTail = 0
  /\ receiverDurable = 0
  /\ senderAck = 0
  /\ pruned = 0
  /\ writerHeld = TRUE
  /\ activeEpoch = 1
  /\ retiredEpochs = {}
  /\ checkpointFloor = 0
  /\ lastEventTime = 0
  /\ blocked = FALSE
  /\ receiverObserved = 0

Admit ==
  /\ writerHeld
  /\ ~blocked
  /\ walTail < MaxSeq
  /\ walTail' = walTail + 1
  /\ lastEventTime' = lastEventTime + 1
  /\ lastEventTime' >= checkpointFloor
  /\ UNCHANGED <<receiverDurable, senderAck, pruned, writerHeld,
                  activeEpoch, retiredEpochs, checkpointFloor,
                  blocked, receiverObserved>>

Commit ==
  /\ ~blocked
  /\ receiverDurable < walTail
  /\ receiverDurable' = receiverDurable + 1
  /\ receiverObserved' = receiverDurable'
  /\ UNCHANGED <<walTail, senderAck, pruned, writerHeld,
                  activeEpoch, retiredEpochs, checkpointFloor,
                  lastEventTime, blocked>>

RememberAck ==
  /\ ~blocked
  /\ senderAck < receiverDurable
  /\ senderAck' = receiverDurable
  /\ UNCHANGED <<walTail, receiverDurable, pruned, writerHeld,
                  activeEpoch, retiredEpochs, checkpointFloor,
                  lastEventTime, blocked, receiverObserved>>

Prune ==
  /\ ~blocked
  /\ pruned < senderAck
  /\ pruned' = senderAck
  /\ UNCHANGED <<walTail, receiverDurable, senderAck, writerHeld,
                  activeEpoch, retiredEpochs, checkpointFloor,
                  lastEventTime, blocked, receiverObserved>>

Checkpoint ==
  /\ writerHeld
  /\ ~blocked
  /\ checkpointFloor' = lastEventTime
  /\ UNCHANGED <<walTail, receiverDurable, senderAck, pruned,
                  writerHeld, activeEpoch, retiredEpochs,
                  lastEventTime, blocked, receiverObserved>>

Crash ==
  /\ writerHeld
  /\ writerHeld' = FALSE
  /\ UNCHANGED <<walTail, receiverDurable, senderAck, pruned,
                  activeEpoch, retiredEpochs, checkpointFloor,
                  lastEventTime, blocked, receiverObserved>>

AcquireWriter ==
  /\ ~writerHeld
  /\ ~blocked
  /\ writerHeld' = TRUE
  /\ UNCHANGED <<walTail, receiverDurable, senderAck, pruned,
                  activeEpoch, retiredEpochs, checkpointFloor,
                  lastEventTime, blocked, receiverObserved>>

ReceiverRollbackFault ==
  /\ ~blocked
  /\ senderAck > 0
  /\ receiverObserved' = senderAck - 1
  /\ blocked' = TRUE
  /\ UNCHANGED <<walTail, receiverDurable, senderAck, pruned,
                  writerHeld, activeEpoch, retiredEpochs,
                  checkpointFloor, lastEventTime>>

SplitHistoryFault ==
  /\ ~blocked
  /\ receiverDurable > 0
  /\ blocked' = TRUE
  /\ UNCHANGED <<walTail, receiverDurable, senderAck, pruned,
                  writerHeld, activeEpoch, retiredEpochs,
                  checkpointFloor, lastEventTime, receiverObserved>>

EpochTransition ==
  /\ writerHeld
  /\ ~blocked
  /\ activeEpoch = 1
  /\ activeEpoch' = 2
  /\ retiredEpochs' = retiredEpochs \cup {1}
  /\ walTail' = 0
  /\ receiverDurable' = 0
  /\ senderAck' = 0
  /\ pruned' = 0
  /\ receiverObserved' = 0
  /\ UNCHANGED <<writerHeld, checkpointFloor, lastEventTime, blocked>>

UnsafePrune ==
  /\ EnableUnsafe
  /\ senderAck < MaxSeq
  /\ pruned' = senderAck + 1
  /\ UNCHANGED <<walTail, receiverDurable, senderAck, writerHeld,
                  activeEpoch, retiredEpochs, checkpointFloor,
                  lastEventTime, blocked, receiverObserved>>

Next == Admit \/ Commit \/ RememberAck \/ Prune \/ Checkpoint \/ Crash \/
        AcquireWriter \/ ReceiverRollbackFault \/ SplitHistoryFault \/
        EpochTransition \/ UnsafePrune

TypeOK ==
  /\ walTail \in 0..MaxSeq
  /\ receiverDurable \in 0..MaxSeq
  /\ senderAck \in 0..MaxSeq
  /\ pruned \in 0..MaxSeq
  /\ writerHeld \in BOOLEAN
  /\ activeEpoch \in {1,2}
  /\ retiredEpochs \subseteq {1,2}
  /\ checkpointFloor \in Nat
  /\ lastEventTime \in Nat
  /\ blocked \in BOOLEAN
  /\ receiverObserved \in 0..MaxSeq

AckSafe == senderAck <= receiverDurable
PruneSafe == pruned <= senderAck
ReceiverNotAhead == receiverDurable <= walTail
RetiredNeverCurrent == activeEpoch \notin retiredEpochs
TemporalFloorSafe == lastEventTime >= checkpointFloor
RollbackDetected == (receiverObserved < senderAck) => blocked

Spec == Init /\ [][Next]_vars
====
