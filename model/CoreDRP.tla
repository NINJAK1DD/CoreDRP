---- MODULE CoreDRP ----
EXTENDS Naturals
CONSTANT MaxSeq
VARIABLES walTail, receiverDurable, senderAck, pruned, retired
vars == <<walTail, receiverDurable, senderAck, pruned, retired>>
Init == /\ walTail=0 /\ receiverDurable=0 /\ senderAck=0 /\ pruned=0 /\ retired=FALSE
Admit == /\ ~retired /\ walTail<MaxSeq /\ walTail'=walTail+1 /\ UNCHANGED <<receiverDurable,senderAck,pruned,retired>>
Commit == /\ receiverDurable<walTail /\ receiverDurable'=receiverDurable+1 /\ UNCHANGED <<walTail,senderAck,pruned,retired>>
RememberAck == /\ senderAck<receiverDurable /\ senderAck'=receiverDurable /\ UNCHANGED <<walTail,receiverDurable,pruned,retired>>
Prune == /\ pruned<senderAck /\ pruned'=senderAck /\ UNCHANGED <<walTail,receiverDurable,senderAck,retired>>
Retire == /\ retired'=TRUE /\ UNCHANGED <<walTail,receiverDurable,senderAck,pruned>>
Next == Admit \/ Commit \/ RememberAck \/ Prune \/ Retire
TypeOK == /\ walTail\in 0..MaxSeq /\ receiverDurable\in 0..MaxSeq /\ senderAck\in 0..MaxSeq /\ pruned\in 0..MaxSeq /\ retired\in BOOLEAN
AckSafe == senderAck<=receiverDurable
PruneSafe == pruned<=senderAck
ReceiverNotAhead == receiverDurable<=walTail
Spec == Init /\ [][Next]_vars
====
