# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Read-only, single-scope Bitcoin PPS snapshot comparison. Never authorizes payout."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import uuid
from fractions import Fraction
import psycopg
from psycopg.rows import dict_row
from .wire import Failure, require

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from financial_semantics import decimal, amount, pps_liability

SOURCE_REVISION='2702579ca7281509572dbf722fbffcf306c99aed'
MAX_ROWS=10000

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def timestamp(value):
    if isinstance(value,str):value=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    require(isinstance(value,dt.datetime) and value.tzinfo is not None,'SHADOW_INVALID_TIME')
    return value.astimezone(dt.timezone.utc)
def time_text(value):return timestamp(value).isoformat().replace('+00:00','Z')
def number(value):
    text=format(value,'f')
    if '.' in text:text=text.rstrip('0').rstrip('.')
    return text

def validate_policy(policy,scope,start,end):
    require(re.fullmatch(r'[A-Za-z0-9._-]{1,64}',scope) is not None,'SHADOW_INVALID_SCOPE')
    require(policy.get('scope')==scope and policy.get('scheme')=='PPS' and policy.get('coin')=='bitcoin','SHADOW_UNSUPPORTED_POLICY')
    require(0<decimal(policy['retained_percent'])<=100,'SHADOW_UNSUPPORTED_POLICY')
    require(timestamp(policy['from'])<=start<end<=timestamp(policy['until']),'SHADOW_POLICY_COVERAGE')

def snapshot(dsn,scope,start,end,policy):
    start=timestamp(start);end=timestamp(end);validate_policy(policy,scope,start,end)
    # Set read-only before the first SQL command. Every table is schema-qualified;
    # no source schema creation, writes, wallet RPCs or application calls exist.
    with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=5) as db:
        db.read_only=True;db.isolation_level=psycopg.IsolationLevel.REPEATABLE_READ
        with db.transaction():
            db.execute("SET LOCAL search_path=pg_catalog")
            db.execute("SET LOCAL statement_timeout='10s'")
            db.execute("SET LOCAL lock_timeout='2s'")
            meta=db.execute('SELECT current_database() AS database, pg_current_snapshot()::text AS snapshot, transaction_timestamp() AS captured_at, current_setting(\'transaction_read_only\') AS read_only').fetchone()
            require(meta['database'].startswith(('miningcore_shadow_','coredrp_ref_')),'ISOLATED_DATABASE_REQUIRED')
            params=(scope,start,end,MAX_ROWS+1)
            shares=db.execute('SELECT accountingid,miner,difficulty,networkdifficulty,rewardbasissatoshis,created FROM public.shares WHERE poolid=%s AND created>=%s AND created<%s ORDER BY created,accountingid LIMIT %s',params).fetchall()
            credits=db.execute('SELECT accountingid,address,calculatedamount,creditedamount,difficulty,networkdifficulty,rewardbasissatoshis,created FROM public.pps_share_credits WHERE poolid=%s AND created>=%s AND created<%s ORDER BY created,accountingid LIMIT %s',params).fetchall()
            require(len(shares)<=MAX_ROWS and len(credits)<=MAX_ROWS,'SHADOW_EXPORT_LIMIT')
            tags=['pps-share:'+str(row['accountingid']).replace('-','') for row in shares+credits if row['accountingid'] is not None]
            changes=db.execute("""SELECT id,address,amount,usage,tags,created
                FROM public.balance_changes
                WHERE poolid=%s AND (
                    (created>=%s AND created<%s AND (
                        usage='PPS share credit' OR 'pps'=ANY(tags) OR
                        EXISTS (SELECT 1 FROM unnest(tags) AS t(tag) WHERE tag LIKE 'pps-share:%%')))
                    OR tags && %s::text[])
                ORDER BY id LIMIT %s""",(scope,start,end,tags,MAX_ROWS+1)).fetchall()
            require(len(changes)<=MAX_ROWS,'SHADOW_EXPORT_LIMIT')
    def convert(rows):
        result=[]
        for row in rows:
            row=dict(row)
            for key in ('difficulty','networkdifficulty'):
                if key in row:row[key+'_bits']=struct.pack('>d',row.pop(key)).hex()
            for key in ('calculatedamount','creditedamount','amount'):
                if key in row:row[key]=number(row[key])
            if 'accountingid' in row:row['accountingid']=str(row['accountingid']) if row['accountingid'] is not None else None
            row['created']=time_text(row['created']);result.append(row)
        return result
    meta['captured_at']=time_text(meta['captured_at'])
    data=dict(version=1,scope=scope,scheme='PPS',from_time=time_text(start),until_time=time_text(end),policy=policy,source_schema_reviewed_at=SOURCE_REVISION,source=meta,shares=convert(shares),credits=convert(credits),balance_changes=convert(changes))
    return {'sha256':digest(data),'data':data}

def compare(export):
    data=export['data'];require(digest(data)==export['sha256'],'SHADOW_EXPORT_DIGEST_MISMATCH')
    require(data['version']==1 and data['scheme']=='PPS','SHADOW_UNSUPPORTED_EXPORT')
    validate_policy(data['policy'],data['scope'],timestamp(data['from_time']),timestamp(data['until_time']))
    differences=[];rounding=[]
    def finding(identity,reason,**detail):differences.append(dict(accounting_id=identity,reason=reason,**detail))
    def index(rows,kind):
        result={}
        for row in rows:
            key=row['accountingid']
            if key is None:finding(None,'share_has_no_durable_accounting_identity');continue
            require(key not in result,'SHADOW_DUPLICATE_ACCOUNTING_ID')
            result[key]=row
        return result
    shares=index(data['shares'],'share');credits=index(data['credits'],'credit')
    changes={}
    for change in data['balance_changes']:
        tags=[t for t in (change['tags'] or []) if t.startswith('pps-share:')]
        if len(tags)!=1:
            finding(None,'ambiguous_balance_credit_tags',balance_change_id=change['id']);continue
        if not re.fullmatch(r'pps-share:[0-9a-f]{32}',tags[0]):
            finding(None,'invalid_balance_credit_tag',balance_change_id=change['id']);continue
        identity=str(uuid.UUID(hex=tags[0][10:]))
        if identity not in shares and identity not in credits:
            finding(identity,'balance_credit_without_source_rows',balance_change_id=change['id'])
        try:ledger_amount=decimal(change['amount'])
        except (ValueError,TypeError):
            ledger_amount=None
            finding(identity,'balance_credit_mismatch',balance_change_id=change['id'],field='amount',actual=change['amount'],detail='noncanonical ledger amount')
        changes.setdefault(tags[0],[]).append((change,ledger_amount))
    totals={};baseline={};recipient_credits={}
    for key in sorted(set(shares)|set(credits)):
        share=shares.get(key);credit=credits.get(key)
        if not share:finding(key,'credit_without_retained_share');continue
        if not credit:finding(key,'share_without_pps_credit');continue
        mismatch=[field for field in ('difficulty_bits','networkdifficulty_bits','rewardbasissatoshis','created') if share[field]!=credit[field]]
        if share['miner']!=credit['address']:mismatch.append('recipient')
        if mismatch:finding(key,'credit_source_mismatch',fields=mismatch)
        try:
            expected=pps_liability(share['rewardbasissatoshis'],share['difficulty_bits'],share['networkdifficulty_bits'],data['policy']['retained_percent'])
            actual=decimal(credit['calculatedamount']);paid=decimal(credit['creditedamount'])
        except (ValueError,TypeError):finding(key,'invalid_liability_input');continue
        miner=share['miner'];totals[miner]=totals.get(miner,Fraction(0))+decimal(expected)
        recipient=credit['address'];baseline[recipient]=baseline.get(recipient,Fraction(0))+actual
        recipient_credits.setdefault(recipient,[]).append((timestamp(credit['created']),key,actual,paid))
        if actual!=decimal(expected):finding(key,'calculated_liability_mismatch',reference=expected,baseline=credit['calculatedamount'],delta=str(actual-decimal(expected)))
        # A per-share credit can include the previous sub-12-decimal remainder.
        # We do not invent the historical opening carry from current balances.
        floor=Fraction(actual.numerator*10**12//actual.denominator,10**12)
        ceiling=floor if floor==actual else floor+Fraction(1,10**12)
        if paid not in (floor,ceiling):finding(key,'credited_amount_outside_precision_carry_bounds',calculated=credit['calculatedamount'],credited=credit['creditedamount'])
        elif paid!=actual:rounding.append(dict(accounting_id=key,reason='scale12_rounding_or_carry_requires_opening_remainder',calculated=credit['calculatedamount'],credited=credit['creditedamount'],delta=str(paid-actual),verified=False))
        rows=changes.get('pps-share:'+key.replace('-',''),[])
        if len(rows)!=(1 if paid>0 else 0):finding(key,'balance_credit_count_mismatch',expected=1 if paid>0 else 0,actual=len(rows))
        for row,ledger_amount in rows:
            if row['address']!=credit['address'] or row['usage']!='PPS share credit' or row['created']!=credit['created'] or (ledger_amount is not None and ledger_amount!=paid):
                finding(key,'balance_credit_mismatch',balance_change_id=row['id'])
    # For every prefix p, 0 <= opening + sum(calculated-credited) < unit.
    # Intersect all permissible opening ranges, including the empty prefix.
    # A nonempty intersection establishes possibility, never historical proof.
    unit=Fraction(1,10**12)
    for recipient,rows in sorted(recipient_credits.items()):
        prefix=Fraction(0);lower=Fraction(0);upper=unit
        for _,key,actual,paid in sorted(rows):
            prefix+=actual-paid
            lower=max(lower,-prefix);upper=min(upper,unit-prefix)
            if lower>=upper:
                finding(key,'inconsistent_recipient_carry_history',recipient=recipient,
                        prefix_calculated_minus_credited=str(prefix),
                        opening_lower_inclusive=str(lower),opening_upper_exclusive=str(upper))
                break
    blockers=['authenticated policy/admission history unavailable','relay clock/checkpoint/gap evidence unavailable','historical opening/closing remainder proof unavailable']
    if not shares or not credits:blockers.append('no complete share/credit population')
    if differences:blockers.append('accounting differences require reconciliation')
    return dict(shadow_only=True,eligible=False,scope=data['scope'],scheme='PPS',source_digest=export['sha256'],policy_digest=digest(data['policy']),accounting_matches=bool(shares and credits) and not differences,blocked_reasons=blockers,differences=differences,precision_differences=rounding,reference_totals={k:amount(v) for k,v in sorted(totals.items())},baseline_totals={k:amount(v) for k,v in sorted(baseline.items())})

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='action',required=True)
    export=commands.add_parser('export');export.add_argument('--scope',required=True);export.add_argument('--from',dest='start',required=True);export.add_argument('--until',required=True);export.add_argument('--policy',type=Path,required=True)
    audit=commands.add_parser('compare');audit.add_argument('--input',type=Path,required=True)
    for command in (export,audit):command.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='export':result=snapshot(os.environ['MININGCORE_SHADOW_DSN'],args.scope,args.start,args.until,json.loads(args.policy.read_text()))
    else:result=compare(json.loads(args.input.read_text()))
    # Exclusive creation prevents accidentally replacing retained evidence.
    with args.output.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

if __name__=='__main__':
    try:main()
    except Failure as error:print(error.code,file=sys.stderr);sys.exit(2)
    except (OSError,psycopg.Error,ValueError,KeyError,TypeError):print('SHADOW_EXPORT_OR_INPUT_FAILURE',file=sys.stderr);sys.exit(2)
