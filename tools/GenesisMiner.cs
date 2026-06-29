using System;
using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;

class GenesisMiner
{
    static byte[] HexToBytes(string hex)
    {
        hex = hex.Replace("0x", "").Replace(" ", "").Trim();
        if (hex.Length % 2 != 0) throw new ArgumentException("Hex length must be even");
        byte[] b = new byte[hex.Length / 2];
        for (int i = 0; i < b.Length; i++) b[i] = Convert.ToByte(hex.Substring(i * 2, 2), 16);
        return b;
    }

    static byte[] U32LE(uint v)
    {
        return new byte[] { (byte)v, (byte)(v >> 8), (byte)(v >> 16), (byte)(v >> 24) };
    }

    static byte[] Hash256(byte[] buf, SHA256 sha)
    {
        byte[] h1 = sha.ComputeHash(buf);
        return sha.ComputeHash(h1);
    }

    static int CmpBE(byte[] a, byte[] b)
    {
        for (int i = 0; i < 32; i++)
        {
            int d = a[i] - b[i];
            if (d != 0) return d;
        }
        return 0;
    }

    static void Main(string[] args)
    {
        string merkleHex = null;
        uint nTime = 0, nBits = 0, nVersion = 4;
        long start = 0, stride = 1;
        int threads = Environment.ProcessorCount;

        for (int i = 0; i < args.Length; i++)
        {
            string k = args[i];
            if (k == "--merkle" && i + 1 < args.Length) merkleHex = args[++i];
            else if (k == "--time" && i + 1 < args.Length) nTime = uint.Parse(args[++i]);
            else if (k == "--bits" && i + 1 < args.Length) nBits = Convert.ToUInt32(args[++i], 16);
            else if (k == "--version" && i + 1 < args.Length) nVersion = uint.Parse(args[++i]);
            else if (k == "--start" && i + 1 < args.Length) start = long.Parse(args[++i]);
            else if (k == "--stride" && i + 1 < args.Length) stride = long.Parse(args[++i]);
            else if (k == "--threads" && i + 1 < args.Length) threads = int.Parse(args[++i]);
        }

        if (string.IsNullOrEmpty(merkleHex) || nTime == 0 || nBits == 0)
        {
            Console.WriteLine("Usage: GenesisMiner --merkle <64-hex> --time <uint> --bits <hex> [--version 4] [--start 0] [--stride 1] [--threads N]");
            return;
        }

        SHA256 sha = SHA256.Create();
        byte[] verLE = U32LE(nVersion);
        byte[] prev32 = new byte[32]; // zero
        byte[] merkleBE = HexToBytes(merkleHex);
        if (merkleBE.Length != 32) { Console.WriteLine("Merkle must be 32 bytes."); return; }
        byte[] merkleLE = (byte[])merkleBE.Clone(); Array.Reverse(merkleLE);
        byte[] timeLE = U32LE(nTime);
        byte[] bitsLE = U32LE(nBits);

        int exp = (int)(nBits >> 24);
        uint mant = nBits & 0x00FFFFFFU;
        if (exp < 3 || exp > 32) { Console.WriteLine("Invalid nBits exponent."); return; }
        byte[] target = new byte[32];
        target[exp - 3] = (byte)((mant >> 16) & 0xFF);
        target[exp - 2] = (byte)((mant >> 8) & 0xFF);
        target[exp - 1] = (byte)(mant & 0xFF);

        CancellationTokenSource cts = new CancellationTokenSource();
        ConcurrentQueue<Tuple<uint, byte[], uint>> found = new ConcurrentQueue<Tuple<uint, byte[], uint>>();

        var sw = System.Diagnostics.Stopwatch.StartNew();
        Console.WriteLine(string.Format("Start mining threads={0} time={1} bits=0x{2:X8}", threads, nTime, nBits));

        ParallelOptions po = new ParallelOptions();
        po.MaxDegreeOfParallelism = threads;
        po.CancellationToken = cts.Token;

        try
        {
            Parallel.For(0, threads, po, t =>
            {
                SHA256 shaL = SHA256.Create();
                byte[] hdr = new byte[80];
                Array.Copy(verLE, 0, hdr, 0, 4);
                Array.Copy(prev32, 0, hdr, 4, 32);
                Array.Copy(merkleLE, 0, hdr, 36, 32);
                Array.Copy(timeLE, 0, hdr, 68, 4);
                Array.Copy(bitsLE, 0, hdr, 72, 4);

                long nonce64 = start + t;
                long step = stride * threads;
                long it = 0;

                while (!po.CancellationToken.IsCancellationRequested)
                {
                    uint nonce = (uint)nonce64;
                    Array.Copy(U32LE(nonce), 0, hdr, 76, 4);
                    byte[] hLE = Hash256(hdr, shaL);
                    byte[] hBE = (byte[])hLE.Clone(); Array.Reverse(hBE);

                    if (CmpBE(hBE, target) <= 0)
                    {
                        found.Enqueue(Tuple.Create(nonce, hBE, nTime));
                        cts.Cancel();
                        return;
                    }
                    nonce64 += step;
                    it++;
                    if ((it & 0xFFFFF) == 0)
                    {
                        double mh = (it / Math.Max(1.0, sw.Elapsed.TotalSeconds)) / 1e6;
                        Console.WriteLine(string.Format("[t{0}] ~{1:F2}M @ {2:F1} MH/s last={3}", t, it / 1e6, mh, nonce));
                    }
                }
            });
        }
        catch (OperationCanceledException) { }

        Tuple<uint, byte[], uint> res;
        if (found.TryDequeue(out res))
        {
            string hashHex = BitConverter.ToString(res.Item2).Replace("-", "").ToLower();
            Console.WriteLine(string.Format("FOUND nonce={0}", res.Item1));
            Console.WriteLine(string.Format("HASH  = {0}", hashHex));
            Console.WriteLine(string.Format("MERKLE= {0}", merkleHex.ToLower()));
            Console.WriteLine(string.Format("HDR   v={0} time={1} bits=0x{2:X8} nonce={3}", nVersion, res.Item3, nBits, res.Item1));
        }
        else
        {
            Console.WriteLine("Not found in current window.");
        }
    }
}
