using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

var root = Directory.GetCurrentDirectory();
using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "docs/coredrp-v1-core-hash-vectors.json")));
var data = doc.RootElement;
var tags = data.GetProperty("domain_tags_ascii");
byte[] Pay = Encoding.ASCII.GetBytes(tags.GetProperty("payload").GetString()!);
byte[] Evt = Encoding.ASCII.GetBytes(tags.GetProperty("event").GetString()!);
byte[] Gen = Encoding.ASCII.GetBytes(tags.GetProperty("genesis").GetString()!);

static byte[] U8(int n) => [(byte)n];
static byte[] U16(int n) { var b = new byte[2]; BinaryPrimitives.WriteUInt16BigEndian(b, (ushort)n); return b; }
static byte[] U32(uint n) { var b = new byte[4]; BinaryPrimitives.WriteUInt32BigEndian(b, n); return b; }
static byte[] U64(ulong n) { var b = new byte[8]; BinaryPrimitives.WriteUInt64BigEndian(b, n); return b; }
static byte[] I64(long n) { var b = new byte[8]; BinaryPrimitives.WriteInt64BigEndian(b, n); return b; }
static byte[] Cat(params byte[][] xs) { var r = new byte[xs.Sum(x => x.Length)]; int o = 0; foreach(var x in xs) { Buffer.BlockCopy(x, 0, r, o, x.Length); o += x.Length; } return r; }
static byte[] H(byte[] b) => SHA256.HashData(b);
static string Hex(byte[] b) => Convert.ToHexString(b).ToLowerInvariant();
static byte[] UuidBytes(string s) => Convert.FromHexString(Guid.Parse(s).ToString("N"));

foreach(var c in data.GetProperty("chains").EnumerateArray()) {
    var sender = UuidBytes(c.GetProperty("sender_id").GetString()!);
    var epoch = UuidBytes(c.GetProperty("log_epoch").GetString()!);
    if(Hex(sender) != c.GetProperty("sender_id_bytes_hex").GetString() || Hex(epoch) != c.GetProperty("log_epoch_bytes_hex").GetString()) throw new Exception("RFC9562 UUID order");
    int lane = c.GetProperty("lane_id").GetInt32();
    var gp = Cat(Gen, sender, epoch, U8(lane));
    if(Hex(gp) != c.GetProperty("genesis_preimage_hex").GetString()) throw new Exception("genesis preimage");
    var genesis = H(gp);
    if(Hex(genesis) != c.GetProperty("genesis_chain_sha256").GetString()) throw new Exception("genesis hash");
    var chain = c.TryGetProperty("synthetic_previous_chain_sha256", out var synth) ? Convert.FromHexString(synth.GetString()!) : genesis;
    foreach(var e in c.GetProperty("events").EnumerateArray()) {
        ulong seq = e.GetProperty("sequence").GetUInt64();
        int et = Convert.ToInt32(e.GetProperty("event_type").GetString(), 16);
        if(et < 0 || et > 65535 || lane < 0 || lane > 255 || seq == 0 || seq > long.MaxValue) throw new Exception("range");
        var rid = UuidBytes(e.GetProperty("relay_event_id").GetString()!);
        var scope = Convert.FromHexString(e.GetProperty("scope_hex").GetString()!);
        long tm = e.GetProperty("event_time_unix_ms").GetInt64();
        var payload = Convert.FromHexString(e.GetProperty("payload_hex").GetString()!);
        var ph = H(Cat(Pay, U32((uint)payload.Length), payload));
        var pre = Cat(Evt, chain, sender, epoch, U8(lane), U64(seq), U16(et), rid, U16(scope.Length), scope, I64(tm), ph);
        if(Hex(ph) != e.GetProperty("payload_hash_sha256").GetString() || Hex(pre) != e.GetProperty("event_preimage_hex").GetString()) throw new Exception("event vector");
        chain = H(pre);
        if(Hex(chain) != e.GetProperty("chain_hash_sha256").GetString()) throw new Exception("event hash");
    }
    if(Hex(chain) != c.GetProperty("terminal_chain_sha256").GetString()) throw new Exception("terminal");
}

var ms = data.GetProperty("max_scope_case");
var mss = UuidBytes(ms.GetProperty("sender_id").GetString()!);
var mse = UuidBytes(ms.GetProperty("log_epoch").GetString()!);
int msl = ms.GetProperty("lane_id").GetInt32();
var mschain = H(Cat(Gen, mss, mse, U8(msl)));
var pat = ms.GetProperty("scope_pattern");
var mscope = Enumerable.Repeat(Convert.FromHexString(pat.GetProperty("byte_hex").GetString()!)[0], pat.GetProperty("count").GetInt32()).ToArray();
var mp = Convert.FromHexString(ms.GetProperty("payload_hex").GetString()!);
var mph = H(Cat(Pay, U32((uint)mp.Length), mp));
var mpre = Cat(Evt, mschain, mss, mse, U8(msl), U64(ms.GetProperty("sequence").GetUInt64()), U16(Convert.ToInt32(ms.GetProperty("event_type").GetString(), 16)), UuidBytes(ms.GetProperty("relay_event_id").GetString()!), U16(mscope.Length), mscope, I64(ms.GetProperty("event_time_unix_ms").GetInt64()), mph);
var comp = ms.GetProperty("event_preimage_components");
var expected = Cat(Convert.FromHexString(comp.GetProperty("prefix_hex").GetString()!), Enumerable.Repeat(Convert.FromHexString(comp.GetProperty("scope_repeat_byte_hex").GetString()!)[0], comp.GetProperty("scope_repeat_count").GetInt32()).ToArray(), Convert.FromHexString(comp.GetProperty("suffix_hex").GetString()!));
if(!mpre.SequenceEqual(expected) || Hex(H(mpre)) != ms.GetProperty("chain_hash_sha256").GetString()) throw new Exception("max scope");

Console.WriteLine("CoreDRP C# current Core 1.1 hash vectors: OK");
