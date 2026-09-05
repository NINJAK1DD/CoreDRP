using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

var root = Directory.GetCurrentDirectory();
using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "docs/coredrp-v1-test-vectors.json")));
var data = doc.RootElement;
var tags = data.GetProperty("domain_tags_ascii");
byte[] Pay = Encoding.ASCII.GetBytes(tags.GetProperty("payload").GetString()!);
byte[] Evt = Encoding.ASCII.GetBytes(tags.GetProperty("event").GetString()!);
byte[] Gen = Encoding.ASCII.GetBytes(tags.GetProperty("genesis").GetString()!);
byte[] Con = Encoding.ASCII.GetBytes(tags.GetProperty("contract").GetString()!);
byte[] Adm = Encoding.ASCII.GetBytes(tags.GetProperty("admin").GetString()!);

static byte[] U8(int n) => [(byte)n];
static byte[] U16(int n) { var b=new byte[2]; BinaryPrimitives.WriteUInt16BigEndian(b,(ushort)n); return b; }
static byte[] U32(uint n) { var b=new byte[4]; BinaryPrimitives.WriteUInt32BigEndian(b,n); return b; }
static byte[] U64(ulong n) { var b=new byte[8]; BinaryPrimitives.WriteUInt64BigEndian(b,n); return b; }
static byte[] I64(long n) { var b=new byte[8]; BinaryPrimitives.WriteInt64BigEndian(b,n); return b; }
static byte[] Cat(params byte[][] xs) { var r=new byte[xs.Sum(x=>x.Length)]; var o=0; foreach(var x in xs){ Buffer.BlockCopy(x,0,r,o,x.Length); o+=x.Length; } return r; }
static byte[] H(byte[] b) => SHA256.HashData(b);
static string Hex(byte[] b) => Convert.ToHexString(b).ToLowerInvariant();
static byte[] UuidBytes(string s) => Convert.FromHexString(Guid.Parse(s).ToString("N"));

foreach(var c in data.GetProperty("chains").EnumerateArray())
{
    var sender=UuidBytes(c.GetProperty("sender_id").GetString()!);
    if(Hex(sender)!=c.GetProperty("sender_id_bytes_hex").GetString()) throw new Exception("RFC9562 sender UUID order");
    var epoch=UuidBytes(c.GetProperty("log_epoch").GetString()!);
    if(Hex(epoch)!=c.GetProperty("log_epoch_bytes_hex").GetString()) throw new Exception("RFC9562 epoch UUID order");
    var lane=c.GetProperty("lane_id").GetInt32();
    var genesisPre=Cat(Gen,sender,epoch,U8(lane));
    if(Hex(genesisPre)!=c.GetProperty("genesis_preimage_hex").GetString()) throw new Exception("genesis preimage");
    var genesis=H(genesisPre);
    if(Hex(genesis)!=c.GetProperty("genesis_chain_sha256").GetString()) throw new Exception("genesis hash");
    var chain=c.TryGetProperty("synthetic_previous_chain_sha256",out var synth) ? Convert.FromHexString(synth.GetString()!) : genesis;
    foreach(var e in c.GetProperty("events").EnumerateArray())
    {
        var seq=e.GetProperty("sequence").GetUInt64();
        var et=Convert.ToInt32(e.GetProperty("event_type").GetString()!,16);
        if(et<0 || et>65535 || lane<0 || lane>255 || seq==0 || seq>long.MaxValue) throw new Exception("range");
        var rid=UuidBytes(e.GetProperty("relay_event_id").GetString()!);
        if(Hex(rid)!=e.GetProperty("relay_event_id_bytes_hex").GetString()) throw new Exception("relay UUID order");
        var scope=Convert.FromHexString(e.GetProperty("scope_hex").GetString()!);
        var tm=e.GetProperty("event_time_unix_ms").GetInt64();
        var payload=Convert.FromHexString(e.GetProperty("payload_hex").GetString()!);
        var ph=H(Cat(Pay,U32((uint)payload.Length),payload));
        var pre=Cat(Evt,chain,sender,epoch,U8(lane),U64(seq),U16(et),rid,U16(scope.Length),scope,I64(tm),ph);
        if(Hex(ph)!=e.GetProperty("payload_hash_sha256").GetString()) throw new Exception("payload hash");
        if(Hex(pre)!=e.GetProperty("event_preimage_hex").GetString()) throw new Exception("event preimage");
        chain=H(pre);
        if(Hex(chain)!=e.GetProperty("chain_hash_sha256").GetString()) throw new Exception("event hash");
    }
    if(Hex(chain)!=c.GetProperty("terminal_chain_sha256").GetString()) throw new Exception("terminal hash");
}

var ms=data.GetProperty("max_scope_case");
var msSender=UuidBytes(ms.GetProperty("sender_id").GetString()!); var msEpoch=UuidBytes(ms.GetProperty("log_epoch").GetString()!); var msLane=ms.GetProperty("lane_id").GetInt32();
var msChain=H(Cat(Gen,msSender,msEpoch,U8(msLane))); var msScopePattern=ms.GetProperty("scope_pattern");
var msScope=Enumerable.Repeat(Convert.FromHexString(msScopePattern.GetProperty("byte_hex").GetString()!)[0],msScopePattern.GetProperty("count").GetInt32()).ToArray();
var msPayload=Convert.FromHexString(ms.GetProperty("payload_hex").GetString()!); var msPh=H(Cat(Pay,U32((uint)msPayload.Length),msPayload));
var msPre=Cat(Evt,msChain,msSender,msEpoch,U8(msLane),U64(ms.GetProperty("sequence").GetUInt64()),U16(Convert.ToInt32(ms.GetProperty("event_type").GetString()!,16)),UuidBytes(ms.GetProperty("relay_event_id").GetString()!),U16(msScope.Length),msScope,I64(ms.GetProperty("event_time_unix_ms").GetInt64()),msPh);
var components=ms.GetProperty("event_preimage_components");
var componentPre=Cat(Convert.FromHexString(components.GetProperty("prefix_hex").GetString()!),Enumerable.Repeat(Convert.FromHexString(components.GetProperty("scope_repeat_byte_hex").GetString()!)[0],components.GetProperty("scope_repeat_count").GetInt32()).ToArray(),Convert.FromHexString(components.GetProperty("suffix_hex").GetString()!));
if(!msPre.SequenceEqual(componentPre) || Hex(H(msPre))!=ms.GetProperty("chain_hash_sha256").GetString()) throw new Exception("max scope");

byte[] Ascii(string s)=>Encoding.ASCII.GetBytes(s);
var sc=data.GetProperty("semantic_contracts"); var mining=sc.GetProperty("mining"); var m=mining.GetProperty("configuration");
var pid=Ascii(m.GetProperty("profile_id").GetString()!); var scopeAscii=Ascii(m.GetProperty("scope").GetString()!); var coin=Ascii(m.GetProperty("coin_id").GetString()!); var network=Ascii(m.GetProperty("network_id").GetString()!);
var miningSource=Cat(U16(pid.Length),pid,U32(m.GetProperty("profile_major").GetUInt32()),U32(m.GetProperty("profile_minor").GetUInt32()),U16(scopeAscii.Length),scopeAscii,U8(m.GetProperty("payout_scheme").GetInt32()),U16(coin.Length),coin,U16(network.Length),network,U16(m.GetProperty("completeness_policy_version").GetInt32()),U16(m.GetProperty("retention_policy_version").GetInt32()),U8(m.GetProperty("cross_sender_ordering_policy").GetInt32()),U8(m.GetProperty("completeness_mode").GetInt32()),U32(m.GetProperty("permitted_clock_skew_ms").GetUInt32()),U32(m.GetProperty("max_clock_step_ms").GetUInt32()),U32(m.GetProperty("probe_interval_ms").GetUInt32()),U32(m.GetProperty("probe_processing_max_ms").GetUInt32()),U32(m.GetProperty("evidence_expiry_ms").GetUInt32()),U32(m.GetProperty("unknown_grace_ms").GetUInt32()));
if(Hex(miningSource)!=mining.GetProperty("source_bytes_hex").GetString() || Hex(H(miningSource))!=mining.GetProperty("sha256").GetString()) throw new Exception("mining contract");
var miningcore=sc.GetProperty("miningcore"); var mc=miningcore.GetProperty("configuration"); pid=Ascii(mc.GetProperty("profile_id").GetString()!); scopeAscii=Ascii(mc.GetProperty("scope").GetString()!);
var mcSource=Cat(U16(pid.Length),pid,U32(mc.GetProperty("profile_major").GetUInt32()),U32(mc.GetProperty("profile_minor").GetUInt32()),U16(scopeAscii.Length),scopeAscii,U32(mc.GetProperty("accounting_schema_version").GetUInt32()),U32(mc.GetProperty("persistence_schema_version").GetUInt32()),U16(mc.GetProperty("direct_candidate_validation_version").GetInt32()),U16(mc.GetProperty("settlement_policy_version").GetInt32()));
if(Hex(mcSource)!=miningcore.GetProperty("source_bytes_hex").GetString() || Hex(H(mcSource))!=miningcore.GetProperty("sha256").GetString()) throw new Exception("miningcore contract");

static byte[] BuildContract(byte[] Con, JsonElement c)
{
    var profiles=c.GetProperty("profiles").EnumerateArray().Select(p=>new { Id=p.GetProperty("profile_id").GetString()!, Major=p.GetProperty("major").GetUInt32(), Minor=p.GetProperty("minor").GetUInt32(), Digest=p.TryGetProperty("digest_hex",out var d)?Convert.FromHexString(d.GetString()!):null }).OrderBy(p=>p.Id,StringComparer.Ordinal).ThenBy(p=>p.Major).ThenBy(p=>p.Minor).ToList();
    var pb=new List<byte[]>(); foreach(var p in profiles){var id=Encoding.ASCII.GetBytes(p.Id);pb.Add(Cat(U16(id.Length),id,U32(p.Major),U32(p.Minor),U8(p.Digest is null?0:1),p.Digest??Array.Empty<byte>()));}
    var scopes=c.GetProperty("scope_contracts").EnumerateArray().Select(x=>new {Scope=Convert.FromHexString(x.GetProperty("scope_hex").GetString()!),Id=x.GetProperty("profile_id").GetString()!,Digest=Convert.FromHexString(x.GetProperty("digest_hex").GetString()!)}).OrderBy(x=>Hex(x.Scope),StringComparer.Ordinal).ThenBy(x=>x.Id,StringComparer.Ordinal).ToList();
    var sb=new List<byte[]>(); foreach(var x in scopes){var id=Encoding.ASCII.GetBytes(x.Id);sb.Add(Cat(U16(x.Scope.Length),x.Scope,U16(id.Length),id,x.Digest));}
    var types=c.GetProperty("event_types").EnumerateArray().Select(x=>Convert.ToInt32(x.GetString()!,16)).Order().ToList();
    return Cat(Con,U32(c.GetProperty("core_major").GetUInt32()),U32(c.GetProperty("core_minor").GetUInt32()),U8(c.GetProperty("lane_id").GetInt32()),U16(profiles.Count),Cat(pb.ToArray()),U16(scopes.Count),Cat(sb.ToArray()),U16(types.Count),Cat(types.Select(U16).ToArray()));
}
var contract=data.GetProperty("contract_binding"); var contractPre=BuildContract(Con,contract);
if(Hex(contractPre)!=contract.GetProperty("preimage_hex").GetString() || Hex(H(contractPre))!=contract.GetProperty("sha256").GetString()) throw new Exception("contract binding");
var no=data.GetProperty("contract_binding_without_digest"); var noProfile=no.GetProperty("profile");
using var noDoc=JsonDocument.Parse($$"""{"core_major":{{no.GetProperty("core_major").GetUInt32()}},"core_minor":{{no.GetProperty("core_minor").GetUInt32()}},"lane_id":{{no.GetProperty("lane_id").GetInt32()}},"profiles":[{"profile_id":"{{noProfile.GetProperty("profile_id").GetString()}}","major":{{noProfile.GetProperty("major").GetUInt32()}},"minor":{{noProfile.GetProperty("minor").GetUInt32()}}}],"scope_contracts":[],"event_types":["0xF000"]}""");
var noPre=BuildContract(Con,noDoc.RootElement);
if(Hex(noPre)!=no.GetProperty("preimage_hex").GetString() || Hex(H(noPre))!=no.GetProperty("sha256").GetString()) throw new Exception("contract no digest");

var admin=data.GetProperty("admin_digest"); var afields=new List<(int Id,byte[] Value)>();
foreach(var f in admin.GetProperty("fields").EnumerateArray()) { var type=f.GetProperty("type").GetString()!; byte[] value=type switch { "uuid"=>UuidBytes(f.GetProperty("value").GetString()!), "uint64"=>U64(f.GetProperty("value").GetUInt64()), "utf8"=>Encoding.UTF8.GetBytes(f.GetProperty("value").GetString()!), _=>throw new Exception("admin type") }; afields.Add((f.GetProperty("field_id").GetInt32(),value)); }
afields=afields.OrderBy(x=>x.Id).ToList(); var body=Cat(U16(1),U16(afields.Count),Cat(afields.Select(x=>Cat(U16(x.Id),U32((uint)x.Value.Length),x.Value)).ToArray())); var adminPre=Cat(Adm,U16(admin.GetProperty("action_type").GetInt32()),U32((uint)body.Length),body);
if(Hex(body)!=admin.GetProperty("canonical_body_hex").GetString() || Hex(adminPre)!=admin.GetProperty("preimage_hex").GetString() || Hex(H(adminPre))!=admin.GetProperty("sha256").GetString()) throw new Exception("admin digest");
Console.WriteLine("CoreDRP C# Draft 0.3 vectors: OK");
