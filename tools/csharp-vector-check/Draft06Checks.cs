using System.Buffers.Binary;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text.Json;

internal static class Draft06Checks
{
    static byte[] U16(int n){var b=new byte[2];BinaryPrimitives.WriteUInt16BigEndian(b,(ushort)n);return b;}
    static byte[] U32(uint n){var b=new byte[4];BinaryPrimitives.WriteUInt32BigEndian(b,n);return b;}
    static byte[] Cat(params byte[][] xs){var r=new byte[xs.Sum(x=>x.Length)];int o=0;foreach(var x in xs){Buffer.BlockCopy(x,0,r,o,x.Length);o+=x.Length;}return r;}
    static string Hex(byte[] b)=>Convert.ToHexString(b).ToLowerInvariant();
    [ModuleInitializer]
    internal static void Init()
    {
        var root=Directory.GetCurrentDirectory();
        using var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"docs/coredrp-v1-draft06-vectors.json")));
        var d=doc.RootElement;
        foreach(var groupName in new[]{"semantic_contracts","network_policies"})
        {
            foreach(var p in d.GetProperty(groupName).EnumerateObject())
            {
                var src=Convert.FromHexString(p.Value.GetProperty("source_hex").GetString()!);
                if(Hex(SHA256.HashData(src))!=p.Value.GetProperty("sha256").GetString())throw new Exception("Draft 0.6 digest "+groupName+"/"+p.Name);
            }
        }
        var c=d.GetProperty("contract_binding");
        var pre=Convert.FromHexString(c.GetProperty("preimage_hex").GetString()!);
        if(Hex(SHA256.HashData(pre))!=c.GetProperty("sha256").GetString())throw new Exception("Draft 0.6 epoch contract binding");
        if(!System.Text.Encoding.ASCII.GetString(pre).StartsWith("CoreDRP1-CONTRACT",StringComparison.Ordinal))throw new Exception("Draft 0.6 contract domain");
        Console.WriteLine("CoreDRP C# Draft 0.6 freeze vectors: OK");
    }
}
