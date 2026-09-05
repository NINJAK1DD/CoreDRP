using System.Buffers.Binary;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

// Independent typed reconstruction; golden preimages are compared, never trusted as inputs.
internal static class EncodingChecks
{
    static readonly UTF8Encoding Utf8=new(false,true);
    static byte[] Cat(params byte[][] xs)=>xs.SelectMany(x=>x).ToArray();
    static byte[] Num(ulong n,int width){var b=new byte[width];for(int i=width-1;i>=0;i--){b[i]=(byte)(n&255);n>>=8;}if(n!=0)throw new Exception("integer overflow");return b;}
    static byte[] Lp(byte[] b)=>Cat(Num((ulong)b.Length,4),b);
    static string Hex(byte[] b)=>Convert.ToHexString(b).ToLowerInvariant();
    static byte[] Encode(JsonElement schemas,string name,JsonElement record)
    {
        var fields=schemas.GetProperty(name).EnumerateArray().ToArray();
        var keys=record.EnumerateObject().Select(x=>x.Name).ToHashSet();
        if(!keys.SetEquals(fields.Select(x=>x.GetProperty("name").GetString()!)))throw new Exception("record fields");
        return Cat(Num(1,2),Cat(fields.Select(f=>Value(schemas,f.GetProperty("type").GetString()!,record.GetProperty(f.GetProperty("name").GetString()!))).ToArray()));
    }
    static byte[] Value(JsonElement schemas,string type,JsonElement v)
    {
        if(type.StartsWith('?'))return v.ValueKind==JsonValueKind.Null?new byte[]{0}:Cat(new byte[]{1},Value(schemas,type[1..],v));
        if(type.StartsWith("array:")){
            string child=type[6..];var entries=v.EnumerateArray().Select(x=>(Json:x,Bytes:Encode(schemas,child,x))).ToList();
            if(child=="CommitmentRequestV1"){
                if(entries.Select(x=>x.Json.GetProperty("output_index").GetUInt32()).Distinct().Count()!=entries.Count)throw new Exception("duplicate index");
                entries.Sort((a,b)=>a.Json.GetProperty("output_index").GetUInt32().CompareTo(b.Json.GetProperty("output_index").GetUInt32()));
            }else entries.Sort((a,b)=>a.Bytes.AsSpan().SequenceCompareTo(b.Bytes));
            return Cat(Num((ulong)entries.Count,4),Cat(entries.Select(x=>Lp(x.Bytes)).ToArray()));
        }
        if(schemas.TryGetProperty(type,out _))return Lp(Encode(schemas,type,v));
        if(type=="i64"){var b=new byte[8];BinaryPrimitives.WriteInt64BigEndian(b,v.GetInt64());return b;}
        if(type=="u8"||type=="u16"||type=="u32"||type=="u64")return Num(v.GetUInt64(),int.Parse(type[1..])/8);
        if(type=="bool")return new byte[]{v.GetBoolean()?(byte)1:(byte)0};
        if(type=="f64"){
            double d=v.GetDouble();if(!double.IsFinite(d)||d<0)throw new Exception("float");
            var b=new byte[8];BinaryPrimitives.WriteInt64BigEndian(b,BitConverter.DoubleToInt64Bits(d));return b;
        }
        if(type=="bytes"||type=="uuid16"||type=="hash32"){
            var b=Convert.FromHexString(v.GetString()!);
            if(type=="bytes")return Lp(b);
            if(b.Length!=(type=="uuid16"?16:32)||(type=="uuid16"&&b.All(x=>x==0)))throw new Exception("fixed bytes");
            return b;
        }
        string text=v.GetString()!;
        if(type=="ascii"&&text.Any(x=>x>127))throw new Exception("ASCII");
        if(type!="ascii"&&type!="utf8")throw new Exception("unknown type");
        return Lp(Utf8.GetBytes(text));
    }
    static string[] AdminTypes(int a)=>a switch {
        4=>new[]{"uuid16","u64","uuid16","u8","uuid16","u64","hash32","uuid16","i64","i64","utf8"},
        5=>new[]{"uuid16","u64","uuid16","u8","uuid16","hash32","i64","i64","utf8"},
        6=>new[]{"uuid16","u64","uuid16","u8","uuid16","u64","hash32","u64","u64","u64","uuid16","u8","utf8"},
        _=>throw new Exception("action")};
    static byte[] Admin(JsonElement schemas,int action,JsonElement fields)
    {
        var types=AdminTypes(action);var values=fields.EnumerateArray().ToArray();
        if(values.Length!=types.Length)throw new Exception("field count");
        var body=Cat(Num(1,2),Num((ulong)values.Length,2));
        for(int i=0;i<values.Length;i++){
            if(values[i].GetProperty("id").GetInt32()!=i+1)throw new Exception("field order");
            var b=Value(schemas,types[i],values[i].GetProperty("value"));if(types[i]=="utf8")b=b[4..];
            body=Cat(body,Num((ulong)i+1,2),Lp(b));
        }
        return body;
    }
    static void ValidateAdmin(int action,byte[] body)
    {
        int offset=0;
        byte[] Take(int n){if(n<0||n>body.Length-offset)throw new Exception("truncated");var x=body.AsSpan(offset,n).ToArray();offset+=n;return x;}
        int Short()=>BinaryPrimitives.ReadUInt16BigEndian(Take(2));
        var types=AdminTypes(action);if(Short()!=1||Short()!=types.Length)throw new Exception("header");
        for(int i=0;i<types.Length;i++){
            if(Short()!=i+1)throw new Exception("order");
            int n=checked((int)BinaryPrimitives.ReadUInt32BigEndian(Take(4)));var v=Take(n);
            int size=types[i] switch {"uuid16"=>16,"u64" or "i64"=>8,"u8"=>1,"hash32"=>32,_=>-1};
            if(size>=0&&n!=size)throw new Exception("width");
            if(types[i]=="utf8")Utf8.GetString(v);
        }
        if(offset!=body.Length)throw new Exception("trailing");
    }
    static void Reject(Action action){bool rejected=false;try{action();}catch(Exception){rejected=true;}if(!rejected)throw new Exception("invalid accepted");}
    static void Check(byte[] b,JsonElement c,string field){if(Hex(b)!=c.GetProperty(field).GetString())throw new Exception("encoding "+field);}
    [ModuleInitializer]
    internal static void Init()
    {
        using var schemaDoc=JsonDocument.Parse(File.ReadAllText("docs/coredrp-v1-request-schemas.json"));var s=schemaDoc.RootElement;
        using var doc=JsonDocument.Parse(File.ReadAllText("docs/coredrp-v1-review2-vectors.json"));var d=doc.RootElement;
        foreach(var c in d.GetProperty("requests").EnumerateArray()){
            var b=Encode(s,c.GetProperty("kind").GetString()!,c.GetProperty("request"));Check(b,c,"request_hex");
            var q=Utf8.GetBytes(c.GetProperty("scope").GetString()!);
            var p=Cat(Utf8.GetBytes("CoreDRP1-ADMISSION"),Num(c.GetProperty("lane").GetUInt64(),1),Num(c.GetProperty("event_type").GetUInt64(),2),Num((ulong)q.Length,2),q,Lp(b));
            Check(p,c,"preimage_hex");Check(SHA256.HashData(p),c,"sha256");
        }
        foreach(var c in d.GetProperty("admin").EnumerateArray()){
            int a=c.GetProperty("action").GetInt32();var b=Admin(s,a,c.GetProperty("fields"));ValidateAdmin(a,b);Check(b,c,"canonical_body_hex");
            var p=Cat(Utf8.GetBytes("CoreDRP1-ADMIN"),Num((ulong)a,2),Lp(b));Check(p,c,"preimage_hex");Check(SHA256.HashData(p),c,"sha256");
            var duplicate=(byte[])b.Clone();duplicate[27]=1;Reject(()=>ValidateAdmin(a,duplicate));
            var descending=(byte[])b.Clone();descending[5]=2;descending[27]=1;Reject(()=>ValidateAdmin(a,descending));
            var shortValue=Cat(b[..28],Num(4,4),b[36..40],b[40..]);Reject(()=>ValidateAdmin(a,shortValue));
        }
        var policy=d.GetProperty("activated_policy");var pb=Encode(s,policy.GetProperty("kind").GetString()!,policy.GetProperty("record"));Check(pb,policy,"record_hex");Check(SHA256.HashData(pb),policy,"sha256");
        foreach(var c in d.GetProperty("audits").EnumerateArray()){
            var b=Encode(s,"SettlementAuditBundleV1",c.GetProperty("bundle"));Check(b,c,"bundle_hex");Check(SHA256.HashData(b),c,"sha256");
        }
        Console.WriteLine("CoreDRP independent C# request, ADMIN, activated-policy and retained-audit encodings: OK");
    }
}
