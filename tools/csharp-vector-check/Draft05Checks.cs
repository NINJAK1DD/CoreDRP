using System.Buffers.Binary;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text.Json;

internal static class Draft05Checks
{
    static byte[] U16(int n){var b=new byte[2];BinaryPrimitives.WriteUInt16BigEndian(b,(ushort)n);return b;}
    static byte[] U32(uint n){var b=new byte[4];BinaryPrimitives.WriteUInt32BigEndian(b,n);return b;}
    static byte[] Cat(params byte[][] xs){var r=new byte[xs.Sum(x=>x.Length)];int o=0;foreach(var x in xs){Buffer.BlockCopy(x,0,r,o,x.Length);o+=x.Length;}return r;}
    static string Hex(byte[] b)=>Convert.ToHexString(b).ToLowerInvariant();
    [ModuleInitializer]
    internal static void Init()
    {
        var root=Directory.GetCurrentDirectory();
        using var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"docs/coredrp-v1-draft05-vectors.json")));
        var d=doc.RootElement;
        var a=d.GetProperty("admission_digest");
        var scope=Convert.FromHexString(a.GetProperty("scope_hex").GetString()!);var req=Convert.FromHexString(a.GetProperty("canonical_request_hex").GetString()!);
        var pre=Cat(System.Text.Encoding.ASCII.GetBytes("CoreDRP1-ADMISSION"),[(byte)a.GetProperty("lane").GetInt32()],U16(Convert.ToInt32(a.GetProperty("event_type").GetString(),16)),U16(scope.Length),scope,U32((uint)req.Length),req);
        if(Hex(pre)!=a.GetProperty("preimage_hex").GetString()||Hex(SHA256.HashData(pre))!=a.GetProperty("sha256").GetString())throw new Exception("Draft 0.5 admission digest");
        foreach(var p in d.GetProperty("semantic_contracts").EnumerateObject()){
            var src=Convert.FromHexString(p.Value.GetProperty("source_hex").GetString()!);if(Hex(SHA256.HashData(src))!=p.Value.GetProperty("sha256").GetString())throw new Exception("Draft 0.5 semantic contract "+p.Name);
        }
        foreach(var x in d.GetProperty("admin_order_cases").EnumerateArray()){
            var ids=x.GetProperty("field_ids").EnumerateArray().Select(v=>v.GetInt32()).ToArray();bool strict=true;for(int i=1;i<ids.Length;i++)strict&=ids[i-1]<ids[i];bool width=true;if(x.TryGetProperty("uint64_field_id",out var uf)){var target=uf.GetInt32();var widths=x.GetProperty("widths").EnumerateArray().Select(v=>v.GetInt32()).ToArray();width=widths[Array.IndexOf(ids,target)]==8;}var got=strict&&width?"ACCEPT":"REJECT";if(got!=x.GetProperty("expected").GetString())throw new Exception("Draft 0.5 ADMIN ordering");
        }
        Console.WriteLine("CoreDRP C# Draft 0.5 supplemental vectors: OK");
    }
}
