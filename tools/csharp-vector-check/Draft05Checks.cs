using System.Buffers.Binary;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

internal static class CurrentAdmissionChecks
{
    static byte[] U8(int n)=>[(byte)n];
    static byte[] U16(int n){var b=new byte[2];BinaryPrimitives.WriteUInt16BigEndian(b,(ushort)n);return b;}
    static byte[] U32(uint n){var b=new byte[4];BinaryPrimitives.WriteUInt32BigEndian(b,n);return b;}
    static byte[] U64(ulong n){var b=new byte[8];BinaryPrimitives.WriteUInt64BigEndian(b,n);return b;}
    static byte[] F64(double n){var b=new byte[8];BinaryPrimitives.WriteInt64BigEndian(b,BitConverter.DoubleToInt64Bits(n));return b;}
    static byte[] Cat(params byte[][] xs){var r=new byte[xs.Sum(x=>x.Length)];int o=0;foreach(var x in xs){Buffer.BlockCopy(x,0,r,o,x.Length);o+=x.Length;}return r;}
    static byte[] Lp32(byte[] b)=>Cat(U32((uint)b.Length),b);
    static byte[] Utf8(string s)=>Encoding.UTF8.GetBytes(s);
    static byte[] OptBytes(JsonElement x,string name){var p=x.GetProperty(name);return p.ValueKind==JsonValueKind.Null?U8(0):Cat(U8(1),Lp32(Convert.FromHexString(p.GetString()!)));}
    static byte[] OptText(JsonElement x,string name,bool ascii=false){var p=x.GetProperty(name);if(p.ValueKind==JsonValueKind.Null)return U8(0);var b=(ascii?Encoding.ASCII:Encoding.UTF8).GetBytes(p.GetString()!);return Cat(U8(1),Lp32(b));}
    static string Hex(byte[] b)=>Convert.ToHexString(b).ToLowerInvariant();
    static byte[] MiningShareRequestV1(JsonElement x)=>Cat(
        U16(1),U64(x.GetProperty("block_height").GetUInt64()),
        Lp32(Utf8(x.GetProperty("miner").GetString()!)),Lp32(Utf8(x.GetProperty("worker").GetString()!)),Lp32(Utf8(x.GetProperty("user_agent").GetString()!)),
        F64(x.GetProperty("difficulty").GetDouble()),F64(x.GetProperty("achieved_share_difficulty").GetDouble()),F64(x.GetProperty("actual_difficulty").GetDouble()),F64(x.GetProperty("network_difficulty").GetDouble()),
        Lp32(Utf8(x.GetProperty("source_ip").GetString()!)),Lp32(Utf8(x.GetProperty("source").GetString()!)),Lp32(Utf8(x.GetProperty("session_id").GetString()!)),
        U8(x.GetProperty("is_block_candidate").GetBoolean()?1:0),OptBytes(x,"candidate_hash_hex"),OptText(x,"candidate_kind"),OptText(x,"transaction_confirmation_data"),OptText(x,"block_reward",true));

    [ModuleInitializer]
    internal static void Init()
    {
        var root=Directory.GetCurrentDirectory();
        using var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"docs/coredrp-v1-admission-vectors.json")));
        var d=doc.RootElement;
        var rq=d.GetProperty("mining_share_request_v1");
        var req=MiningShareRequestV1(rq);
        if(Hex(req)!=rq.GetProperty("canonical_request_hex").GetString())throw new Exception("current MiningShare canonical request");
        var a=d.GetProperty("admission_digest");
        if(Hex(req)!=a.GetProperty("canonical_request_hex").GetString())throw new Exception("current request/vector mismatch");
        var scope=Convert.FromHexString(a.GetProperty("scope_hex").GetString()!);
        var pre=Cat(Encoding.ASCII.GetBytes("CoreDRP1-ADMISSION"),U8(a.GetProperty("lane").GetInt32()),U16(Convert.ToInt32(a.GetProperty("event_type").GetString(),16)),U16(scope.Length),scope,U32((uint)req.Length),req);
        if(Hex(pre)!=a.GetProperty("preimage_hex").GetString()||Hex(SHA256.HashData(pre))!=a.GetProperty("sha256").GetString())throw new Exception("current Mining admission digest");
        Console.WriteLine("CoreDRP C# current Mining admission vectors: OK");
    }
}
