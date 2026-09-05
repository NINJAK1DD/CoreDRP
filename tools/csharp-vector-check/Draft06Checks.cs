using System.Buffers.Binary;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

internal static class Draft06Checks
{
    static byte[] U16(int n){var b=new byte[2];BinaryPrimitives.WriteUInt16BigEndian(b,(ushort)n);return b;}
    static byte[] U32(uint n){var b=new byte[4];BinaryPrimitives.WriteUInt32BigEndian(b,n);return b;}
    static byte[] Cat(params byte[][] xs){var r=new byte[xs.Sum(x=>x.Length)];int o=0;foreach(var x in xs){Buffer.BlockCopy(x,0,r,o,x.Length);o+=x.Length;}return r;}
    static byte[] Lp16(byte[] b)=>Cat(U16(b.Length),b);
    static string Hex(byte[] b)=>Convert.ToHexString(b).ToLowerInvariant();
    static int CompareBytes(byte[] a,byte[] b)=>a.AsSpan().SequenceCompareTo(b);

    [ModuleInitializer]
    internal static void Init()
    {
        var root=Directory.GetCurrentDirectory();
        using var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"docs/coredrp-v1-draft06-vectors.json")));
        var d=doc.RootElement;

        foreach(var groupName in new[]{"semantic_contracts","network_policies","adjustment_policies","settlement_policies"})
        foreach(var p in d.GetProperty(groupName).EnumerateObject())
        {
            var src=Convert.FromHexString(p.Value.GetProperty("source_hex").GetString()!);
            if(Hex(SHA256.HashData(src))!=p.Value.GetProperty("sha256").GetString())
                throw new Exception("Draft 0.6 digest "+groupName+"/"+p.Name);
        }

        // Cross-language ordering guard: PPLNSBF canonical bytes must encode the
        // raw-ASCII-sorted block_finder_percentage key before factor.
        var pbf=Convert.FromHexString(d.GetProperty("settlement_policies").GetProperty("pplnsbf_factor_2_blockfinder_5_identity").GetProperty("source_hex").GetString()!);
        var bfp=Encoding.ASCII.GetBytes("block_finder_percentage");
        var fac=Encoding.ASCII.GetBytes("factor");
        if(pbf.AsSpan().IndexOf(bfp)<0 || pbf.AsSpan().IndexOf(fac)<0 || pbf.AsSpan().IndexOf(bfp)>=pbf.AsSpan().IndexOf(fac))
            throw new Exception("Draft 0.6 PPLNSBF canonical key ordering");

        var c=d.GetProperty("contract_binding");
        var profiles=c.GetProperty("profile_entries").EnumerateArray().Select(p=>new {
            Id=Encoding.ASCII.GetBytes(p.GetProperty("profile_id").GetString()!),
            Major=p.GetProperty("major").GetUInt32(),Minor=p.GetProperty("minor").GetUInt32(),
            HasDigest=p.GetProperty("has_digest").GetBoolean(),
            Digest=p.TryGetProperty("digest_hex",out var dg)?Convert.FromHexString(dg.GetString()!):Array.Empty<byte>()
        }).ToList();
        profiles.Sort((a,b)=>{var n=CompareBytes(a.Id,b.Id);if(n!=0)return n;n=a.Major.CompareTo(b.Major);return n!=0?n:a.Minor.CompareTo(b.Minor);});
        var profileBytes=profiles.Select(p=>{
            if(p.HasDigest&&p.Digest.Length!=32)throw new Exception("Draft 0.6 profile digest width");
            return Cat(Lp16(p.Id),U32(p.Major),U32(p.Minor),new[]{p.HasDigest?(byte)1:(byte)0},p.HasDigest?p.Digest:Array.Empty<byte>());
        }).ToArray();

        var scopes=c.GetProperty("scope_contracts").EnumerateArray().Select(s=>new {
            Scope=Convert.FromHexString(s.GetProperty("scope_hex").GetString()!),
            Id=Encoding.ASCII.GetBytes(s.GetProperty("profile_id").GetString()!),
            Major=s.GetProperty("major").GetUInt32(),Minor=s.GetProperty("minor").GetUInt32(),
            Digest=Convert.FromHexString(s.GetProperty("digest_hex").GetString()!)
        }).ToList();
        scopes.Sort((a,b)=>{var n=CompareBytes(a.Scope,b.Scope);if(n!=0)return n;n=CompareBytes(a.Id,b.Id);if(n!=0)return n;n=a.Major.CompareTo(b.Major);return n!=0?n:a.Minor.CompareTo(b.Minor);});
        var scopeBytes=scopes.Select(s=>{
            if(s.Digest.Length!=32)throw new Exception("Draft 0.6 scope digest width");
            return Cat(Lp16(s.Scope),Lp16(s.Id),U32(s.Major),U32(s.Minor),s.Digest);
        }).ToArray();

        var events=c.GetProperty("event_types").EnumerateArray().Select(e=>e.GetInt32()).ToArray();
        if(events.Any(e=>e<0||e>0xffff)||events.Distinct().Count()!=events.Length)throw new Exception("Draft 0.6 event set");
        Array.Sort(events);
        var eventBytes=events.Select(U16).ToArray();

        var reconstructed=Cat(
            Encoding.ASCII.GetBytes("CoreDRP1-CONTRACT"),
            U32(c.GetProperty("core_major").GetUInt32()),U32(c.GetProperty("core_minor").GetUInt32()),
            new[]{(byte)c.GetProperty("lane").GetInt32()},
            U16(profileBytes.Length),Cat(profileBytes),U16(scopeBytes.Length),Cat(scopeBytes),
            U16(eventBytes.Length),Cat(eventBytes));

        if(Hex(reconstructed)!=c.GetProperty("preimage_hex").GetString())throw new Exception("Draft 0.6 structured contract preimage");
        if(Hex(SHA256.HashData(reconstructed))!=c.GetProperty("sha256").GetString())throw new Exception("Draft 0.6 epoch contract binding");
        Console.WriteLine("CoreDRP C# Draft 0.6 final Profile 1.1 freeze vectors: OK");
    }
}
