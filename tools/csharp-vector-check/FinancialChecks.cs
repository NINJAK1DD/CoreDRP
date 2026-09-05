// Copyright 2026 Rob Cooke
// SPDX-License-Identifier: Apache-2.0
using System.Buffers.Binary;
using System.Globalization;
using System.Numerics;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

internal static class FinancialChecks
{
    readonly record struct Rat(BigInteger N, BigInteger D)
    {
        public static Rat operator +(Rat a,Rat b)=>new(a.N*b.D+b.N*a.D,a.D*b.D);
        public static Rat operator -(Rat a,Rat b)=>new(a.N*b.D-b.N*a.D,a.D*b.D);
        public static Rat operator *(Rat a,Rat b)=>new(a.N*b.N,a.D*b.D);
        public static Rat operator /(Rat a,Rat b)=>new(a.N*b.D,a.D*b.N);
        public int Compare(Rat b)=>(N*b.D).CompareTo(b.N*D);
    }
    static Rat R(long n)=>new(n,1);
    static string S(JsonElement x,string key)=>x.GetProperty(key).GetString()!;
    static byte[] B(JsonElement x,string key)=>Convert.FromHexString(S(x,key));
    static Rat Dec(string s)
    {
        var parts=s.Split('.');return new(BigInteger.Parse(string.Concat(parts),CultureInfo.InvariantCulture),BigInteger.Pow(10,parts.Length==1?0:parts[1].Length));
    }
    static Rat Frac(string s)
    {
        var p=s.Split('/');return new(BigInteger.Parse(p[0]),p.Length==1?BigInteger.One:BigInteger.Parse(p[1]));
    }
    static double Float(string h)=>BitConverter.Int64BitsToDouble(unchecked((long)Convert.ToUInt64(h,16)));
    static Rat Exact(string h)
    {
        ulong n=Convert.ToUInt64(h,16);int e=(int)((n>>52)&2047);BigInteger m=n&0xfffffffffffffUL;
        if(e==2047||(n>>63)!=0)throw new Exception("nonfinite/signed difficulty");
        if(e!=0)m+=BigInteger.One<<52;
        int shift=e==0?-1074:e-1075;
        return shift>=0?new(m<<shift,1):new(m,BigInteger.One<<(-shift));
    }
    static string Quotient(string a,string b)
    {
        double q=Float(a)/Float(b);
        if(!double.IsFinite(q)||q<=0)return "REJECT";
        return unchecked((ulong)BitConverter.DoubleToInt64Bits(q)).ToString("x16");
    }
    static string Amount(Rat x)
    {
        var scale=BigInteger.Pow(10,24);var units=x.N*scale/x.D;
        var whole=BigInteger.DivRem(units,scale,out var rem).ToString(CultureInfo.InvariantCulture);
        return rem.IsZero?whole:whole+"."+rem.ToString(CultureInfo.InvariantCulture).PadLeft(24,'0').TrimEnd('0');
    }
    static byte[] U16(int n){var b=new byte[2];BinaryPrimitives.WriteUInt16BigEndian(b,checked((ushort)n));return b;}
    static byte[] U32(int n){var b=new byte[4];BinaryPrimitives.WriteUInt32BigEndian(b,checked((uint)n));return b;}
    static byte[] U64(ulong n){var b=new byte[8];BinaryPrimitives.WriteUInt64BigEndian(b,n);return b;}
    static byte[] Cat(params byte[][] x)=>x.SelectMany(b=>b).ToArray();
    static byte[] Lp(byte[] b)=>Cat(U16(b.Length),b);
    static string Hex(byte[] b)=>Convert.ToHexString(b).ToLowerInvariant();
    static byte[] Utf(JsonElement x,string k)=>Encoding.UTF8.GetBytes(S(x,k));
    static byte[] Effect(JsonElement s,JsonElement x)=>Cat(U16(1),[(byte)x.GetProperty("kind").GetInt32()],Lp(Utf(s,"scope")),Lp(B(s,"settlement_id_hex")),
        B(s,"mining_scope_contract_digest32"),B(s,"miningcore_scope_contract_digest32"),B(x,"identity"),B(x,"sender"),B(x,"epoch"),
        [(byte)x.GetProperty("lane").GetInt32()],U64(x.GetProperty("sequence").GetUInt64()),B(x,"relay"),U16(x.GetProperty("event_type").GetInt32()),B(x,"payload_hash"),Lp(Utf(x,"miner")),Lp(Utf(x,"amount")));
    [ModuleInitializer]
    internal static void Init()
    {
        using var doc=JsonDocument.Parse(File.ReadAllText("docs/coredrp-v1-financial-hardening-vectors.json"));var d=doc.RootElement;
        foreach(var x in d.GetProperty("division_cases").EnumerateArray())
            if(Quotient(S(x,"assigned"),S(x,"network"))!=S(x,"expected"))throw new Exception("independent binary64 quotient");
        foreach(var x in d.GetProperty("windows").EnumerateArray())
        {
            var rows=x.GetProperty("rows").EnumerateArray().ToList();
            rows.Sort((a,b)=>{
                int n=b.GetProperty("time").GetInt64().CompareTo(a.GetProperty("time").GetInt64());if(n!=0)return n;
                n=B(b,"sender").AsSpan().SequenceCompareTo(B(a,"sender"));if(n!=0)return n;
                n=b.GetProperty("sequence").GetUInt64().CompareTo(a.GetProperty("sequence").GetUInt64());
                return n!=0?n:B(b,"relay").AsSpan().SequenceCompareTo(B(a,"relay"));
            });
            var total=R(0);var factor=Dec(S(x,"factor"));int i=0;
            foreach(var r in rows)
            {
                if(total.Compare(factor)>=0)break;
                var score=Exact(Quotient(S(r,"difficulty"),S(r,"network")));var remain=factor-total;
                var contribution=score.Compare(remain)<0?score:remain;
                if(S(r,"accounting_id")!=x.GetProperty("expected_ids")[i].GetString()||
                    contribution.Compare(Frac(x.GetProperty("expected_contributions")[i].GetString()!))!=0||
                    (contribution/score).Compare(Frac(x.GetProperty("expected_fractions")[i].GetString()!))!=0)
                    throw new Exception("independent window boundary");
                total+=contribution;i++;
            }
            if(i!=x.GetProperty("expected_ids").GetArrayLength())throw new Exception("window count");
        }
        foreach(var x in d.GetProperty("pps_cases").EnumerateArray())
        {
            var value=R(x.GetProperty("reward").GetInt64())/R(100000000)*Exact(S(x,"assigned"))/Exact(S(x,"network"))*Dec(S(x,"retained"))/R(100);
            var result=Amount(value);if(result=="0")result="REJECT";
            if(result!=S(x,"expected"))throw new Exception("independent PPS liability");
        }
        var e=d.GetProperty("effects");var context=e.GetProperty("summary_context");var records=new List<byte[]>();int j=0;var totals=new Dictionary<string,Rat>();
        foreach(var x in e.GetProperty("sources").EnumerateArray())
        {
            var pre=Effect(context,x);
            if(Hex(pre)!=e.GetProperty("preimages")[j].GetString())throw new Exception("effect source bytes");
            var record=Cat(U16(1),[(byte)x.GetProperty("kind").GetInt32()],B(x,"identity"),Lp(Utf(x,"miner")),Lp(Utf(x,"amount")),SHA256.HashData(pre));
            if(Hex(record)!=e.GetProperty("records")[j].GetString())throw new Exception("participant bytes");
            records.Add(record);var miner=S(x,"miner");totals[miner]=totals.GetValueOrDefault(miner,R(0))+Dec(S(x,"amount"));j++;
        }
        records.Sort((a,b)=>a.AsSpan().SequenceCompareTo(b));
        var source=Cat(U16(1),U32(records.Count),Cat(records.Select(r=>Cat(U32(r.Length),r)).ToArray()));
        if(Hex(SHA256.HashData(source))!=S(e,"participant_digest"))throw new Exception("participant set digest");
        foreach(var t in totals)if(Amount(t.Value)!=S(e.GetProperty("miner_totals"),t.Key))throw new Exception("miner aggregation");
        Console.WriteLine("CoreDRP C# financial v4 scoring, PPS and effect reconstruction: OK");
    }
}
