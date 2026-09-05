# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Executable Profile 1.1 settlement-policy v5 algorithms; registries are normative."""
from fractions import Fraction
import hashlib
import re
import struct

DEC = re.compile(r'(?:0|[1-9][0-9]{0,13})(?:\.[0-9]{0,23}[1-9])?\Z')
SCOPE = re.compile(rb'[A-Za-z0-9._-]{1,64}\Z')
def decimal(s):
    if not isinstance(s, str) or not DEC.fullmatch(s) or len(s.replace('.', '')) > 38:
        raise ValueError('noncanonical decimal')
    return Fraction(s)

def amount(x):
    if x < 0: raise ValueError('negative amount')
    n = x.numerator * 10**24 // x.denominator
    s = str(n // 10**24)
    if n % 10**24: s += '.' + str(n % 10**24).zfill(24).rstrip('0')
    decimal(s)
    return s

def binary64(bits):
    n = int(bits, 16)
    if len(bits) != 16 or n >> 63 or ((n >> 52) & 2047) == 2047:
        raise ValueError('not positive finite binary64')
    exponent = (n >> 52) & 2047
    significand = n & ((1 << 52)-1)
    if exponent: significand += 1 << 52
    shift = exponent - 1075 if exponent else -1074
    value = Fraction(significand) * (Fraction(2) ** shift)
    if not value: raise ValueError('zero difficulty')
    return value

def round_binary64(x):
    if x <= 0: raise ValueError('nonpositive quotient')
    e = x.numerator.bit_length() - x.denominator.bit_length()
    if x < Fraction(2)**e: e -= 1
    shift = max(e - 52, -1074)
    scaled = x / Fraction(2)**shift
    n, r = divmod(scaled.numerator, scaled.denominator)
    if 2*r > scaled.denominator or (2*r == scaled.denominator and n % 2): n += 1
    result = Fraction(n) * Fraction(2)**shift
    if result == 0 or result >= Fraction(2)**1024: raise ValueError('rounded quotient underflow/overflow')
    # Encode by integers, never host float or decimal arithmetic.
    if result < Fraction(2)**-1022: bits = int(result * 2**1074)
    else:
        e = result.numerator.bit_length() - result.denominator.bit_length()
        if result < Fraction(2)**e: e -= 1
        sig = int(result / Fraction(2)**(e-52))
        bits = ((e+1023) << 52) | (sig - (1 << 52))
    return f'{bits:016x}'

def tuple_key(x):
    return (x['time'], bytes.fromhex(x['sender']), x['sequence'], bytes.fromhex(x['relay']))

def select_window(rows, factor, page_size=2):
    f = decimal(factor)
    if f <= 0 or page_size <= 0: raise ValueError('window parameter')
    rows = sorted(rows, key=tuple_key, reverse=True)
    if len({tuple_key(r) for r in rows}) != len(rows): raise ValueError('duplicate tuple')
    if len({r['accounting_id'] for r in rows}) != len(rows): raise ValueError('duplicate accounting identity')
    selected = []; total = Fraction(0); cursor = None
    while total < f:
        page = [r for r in rows if cursor is None or tuple_key(r) < cursor][:page_size]
        if not page: break
        for r in page:
            score = binary64(round_binary64(binary64(r['difficulty']) / binary64(r['network'])))
            contribution = min(score, f-total)
            selected.append((r['accounting_id'], contribution, contribution/score))
            total += contribution
            if total == f: break
        cursor = tuple_key(page[-1])
    return selected

def pps_liability(reward, assigned, network, retained, coin='bitcoin', eligible_network=True):
    pct = decimal(retained)
    if coin != 'bitcoin' or not eligible_network or not 0 < pct <= 100 or not 0 < reward <= 2**63-1:
        raise ValueError('PPS policy/input')
    result = amount(Fraction(reward, 10**8)*binary64(assigned)/binary64(network)*pct/100)
    if result == '0': raise ValueError('zero liability')
    return result

def validate_pps(scheme, embedded, **inputs):
    if scheme != 4:
        if embedded is not None: raise ValueError('PPS field in non-PPS scope')
        return
    if embedded != pps_liability(**inputs): raise ValueError('PPS amount mismatch')

def scope_pool(scope, pool):
    if not SCOPE.fullmatch(scope) or scope != pool.encode('utf-8'): raise ValueError('PoolId mismatch')

# No mutation occurs until every scope has passed. Existing durable retries return first.
def admit(state, request, scopes, time):
    if request in state['outcomes']: return state['outcomes'][request]
    for q in scopes:
        p = state['policies'].get(q)
        if not p or not p['activated'] or not p['authorized'] or not p['contract']:
            raise ValueError('missing admission evidence')
        for generation,boundary in state.get('admission_caps',{}).get(q,[]):
            if p.get('generation',0)<generation and time>=boundary: raise ValueError('staged permission withdrawn')
        if not p['from'] <= time < p['until']: raise ValueError('policy coverage')
        if p['mode'] not in ('RELAY_REQUIRED','NO_RELAY_REQUIRED'): raise ValueError('unknown policy')
        if p['mode']=='RELAY_REQUIRED' and not p['member']: raise ValueError('membership')
    if not state.get('admission_history_known',False): raise ValueError('unknown admission history')
    sequence = state.get('last_sequence',0)+1
    state['wal'].append((request,tuple(scopes),time))
    state['last_sequence']=sequence
    for q in scopes:
        state.setdefault('admitted_through',{})[q]=max(time,state.get('admitted_through',{}).get(q,-1))
    state['outcomes'][request]=sequence
    return sequence

def no_live_dependencies(dependencies, uncertainties):
    if any(dependencies.values()): return False
    # Only reconciled uncertainty permits closure; unknown statuses fail closed.
    return all(x == 'RESOLVED_RECONCILED' for x in uncertainties)

def authority_allows(event_type): return event_type in (0x0100,0x0200)

def lp(b): return struct.pack('>H',len(b))+b

def effect_bytes(s, x):
    kind=x['kind']; identity=bytes.fromhex(x['identity']); miner=x['miner'].encode('utf-8'); amt=x['amount'].encode('ascii')
    scope=s['scope'].encode('ascii'); sid=bytes.fromhex(s['settlement_id_hex'])
    if not SCOPE.fullmatch(scope) or not 1<=len(sid)<=65535 or not 1<=len(miner)<=256: raise ValueError('effect text')
    decimal(x['amount'])
    if kind not in (1,2,3,4) or x['lane'] != (1 if kind==4 else 0) or x['event_type'] != (513 if kind==4 else 512): raise ValueError('effect source kind')
    if not 1<=x['sequence']<=2**63-1: raise ValueError('sequence')
    ids=[identity]+[bytes.fromhex(x[k]) for k in ('sender','epoch','relay')]
    if any(len(b)!=16 or not any(b) for b in ids): raise ValueError('UUID')
    digests=[bytes.fromhex(s[k]) for k in ('mining_scope_contract_digest32','miningcore_scope_contract_digest32')]
    payload=bytes.fromhex(x['payload_hash'])
    if any(len(b)!=32 for b in digests+[payload]): raise ValueError('hash')
    return (struct.pack('>HB',1,kind)+lp(scope)+lp(sid)+b''.join(digests)+identity+ids[1]+ids[2]+
            struct.pack('>BQ',x['lane'],x['sequence'])+ids[3]+struct.pack('>H',x['event_type'])+payload+lp(miner)+lp(amt))

def participant_bytes(s,x):
    validated_effect=effect_bytes(s,x)  # Validate sizes/types before any framing.
    return (struct.pack('>HB',1,x['kind'])+bytes.fromhex(x['identity'])+lp(x['miner'].encode())+
            lp(x['amount'].encode('ascii'))+hashlib.sha256(validated_effect).digest())

def participant_digest(s,effects):
    if len({(x['kind'],bytes.fromhex(x['identity'])) for x in effects}) != len(effects): raise ValueError('duplicate participant')
    records=sorted(participant_bytes(s,x) for x in effects)
    return hashlib.sha256(struct.pack('>HI',1,len(records))+b''.join(struct.pack('>I',len(r))+r for r in records)).hexdigest()

def settlement_policy_source(scheme, adjustment_digest, params):
    expected={1:{'factor'},2:{'factor','block_finder_percentage'},3:set(),4:{'retained_reward_percentage'},5:set(),6:set()}
    if scheme not in expected or set(params)!=expected[scheme]: raise ValueError('scheme keys')
    values={k:decimal(v) for k,v in params.items()}
    if 'factor' in values and values['factor']<=0: raise ValueError('factor')
    if 'block_finder_percentage' in values and not 0<=values['block_finder_percentage']<100: raise ValueError('finder percentage')
    if 'retained_reward_percentage' in values and not 0<values['retained_reward_percentage']<=100: raise ValueError('retained percentage')
    if len(adjustment_digest)!=32: raise ValueError('adjustment digest')
    return struct.pack('>HB',3,scheme)+adjustment_digest+struct.pack('>H',len(params))+b''.join(lp(k.encode('ascii'))+lp(params[k].encode('ascii')) for k in sorted(params))

def allocate(selected, reward, finder=None, finder_percentage='0'):
    if len({identity for identity,_,_ in selected})!=len(selected): raise ValueError('duplicate allocation identity')
    r=decimal(reward); p=decimal(finder_percentage)
    if not 0<=p<100 or (p and finder is None): raise ValueError('finder policy')
    total=sum((c for _,c,_ in selected),Fraction(0))
    if total<=0: raise ValueError('empty score window')
    amounts={identity:r*(100-p)/100*c/total for identity,c,_ in selected}
    if finder is not None: amounts[finder]=amounts.get(finder,Fraction(0))+r*p/100
    result={k:amount(v) for k,v in amounts.items()}
    dust=amount(r-sum((decimal(v) for v in result.values()),Fraction(0)))
    return result,dust


def projection_pps(p, policy):
    # Called only with explicit accepting scope context, never live configuration.
    embedded=p.pps_calculated_amount.canonical if p.HasField('pps_calculated_amount') else None
    validate_pps(policy['scheme'],embedded,reward=p.reward_basis_satoshis,
                 assigned=struct.pack('>d',p.share.difficulty).hex(),
                 network=struct.pack('>d',p.share.network_difficulty).hex(),
                 retained=policy.get('retained','100'),coin=policy.get('coin','bitcoin'),
                 eligible_network=policy.get('eligible_network',False))


def activate_required(members, effective, frontier, uncertainty, staged, holders=()):
    if not members or set(members)|set(holders)!=set(staged) or effective<=frontier+uncertainty:
        raise ValueError('unsafe required-mode activation')
    return {'mode':'RELAY_REQUIRED','members':sorted(members),'effective':effective}


# Reference transactional policy distribution model. Callers serialize mutations.
def issue_no_relay(receiver, sender, skew):
    if receiver.get('pending') is not None or receiver['mode']!='NO_RELAY_REQUIRED':
        raise ValueError('policy issuance unavailable')
    receiver['holders'].add(sender)  # persisted BEFORE response, even if response is lost
    receiver['holder_skews'][sender]=max(skew,receiver['holder_skews'].get(sender,0))

def prepare_required(receiver, members, effective, generation, digest, scope='aux'):
    if receiver.get('pending') is not None or not members: raise ValueError('transition conflict')
    receiver['pending']={'required':set(members)|receiver['holders'],'members':set(members),
                         'effective':effective,'generation':generation,'digest':digest,'acks':set(),'scope':scope}

def stage_withdrawal(sender, scope, pending):
    caps=sender.setdefault('admission_caps',{})
    cap=(pending['generation'],pending['effective'])
    if cap not in caps.setdefault(scope,[]): caps[scope].append(cap)
    # Cap stays durable even on rejection: rollback cannot reopen old evidence.
    if not sender.get('admission_history_known',False): raise ValueError('unknown admission history')
    high=max([sender.get('admitted_through',{}).get(scope,-1)]+[t for _,qs,t in sender['wal'] if scope in qs])
    if high>=pending['effective']: raise ValueError('historical admission crosses withdrawal')
    return (pending['generation'],pending['digest'])

def acknowledge_required(receiver, sender, ack):
    p=receiver['pending']
    if sender not in p['required'] or ack!=(p['generation'],p['digest']): raise ValueError('staging mismatch')
    p['acks'].add(sender)

def commit_required(receiver):
    p=receiver['pending']
    if p['required']!=p['members']|receiver['holders'] or p['acks']!=p['required']:
        raise ValueError('missing holder acknowledgement')
    if not receiver.get('committed_history_known',False): raise ValueError('unknown committed history')
    if any(q==p['scope'] and t>=p['effective'] for (_,q),t in receiver.get('committed_through',{}).items()):
        raise ValueError('committed history crosses withdrawal')
    receiver['mode']='RELAY_REQUIRED'
    receiver['pending']=None
