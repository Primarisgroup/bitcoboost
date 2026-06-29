// bbgen.cpp - minimal SHA256d genesis miner for Bitcoin-like header (80 bytes)
// MSVC + bcrypt (Windows) + OpenMP. Public domain.

#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <bcrypt.h>
#pragma comment(lib, "bcrypt.lib")

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <thread>
#include <atomic>
#ifdef _OPENMP
#include <omp.h>
#endif

static inline void le32(uint8_t* p, uint32_t v){ p[0]=uint8_t(v); p[1]=uint8_t(v>>8); p[2]=uint8_t(v>>16); p[3]=uint8_t(v>>24); }

static bool sha256(const uint8_t* data, size_t len, uint8_t out[32]) {
    BCRYPT_ALG_HANDLE hAlg=nullptr; BCRYPT_HASH_HANDLE hHash=nullptr;
    NTSTATUS st = BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
    if(st) return false;
    DWORD objLen=0, cb=0; BCryptGetProperty(hAlg, BCRYPT_OBJECT_LENGTH, (PUCHAR)&objLen, sizeof(objLen), &cb, 0);
    std::vector<BYTE> obj(objLen);
    st = BCryptCreateHash(hAlg, &hHash, obj.data(), (ULONG)obj.size(), nullptr, 0, 0);
    if(st){ BCryptCloseAlgorithmProvider(hAlg,0); return false; }
    st = BCryptHashData(hHash, (PUCHAR)data, (ULONG)len, 0);
    if(st){ BCryptDestroyHash(hHash); BCryptCloseAlgorithmProvider(hAlg,0); return false; }
    st = BCryptFinishHash(hHash, out, 32, 0);
    BCryptDestroyHash(hHash);
    BCryptCloseAlgorithmProvider(hAlg,0);
    return st==0;
}

static inline void sha256d(const uint8_t in[80], uint8_t out_be[32]){
    uint8_t t[32], u[32];
    sha256(in, 80, t);
    sha256(t, 32, u);
    // return big-endian for easy comparison/printing
    for(int i=0;i<32;i++) out_be[i] = u[31 - i];
}

static void hex2bin(const char* hex, uint8_t* out, size_t outlen){
    auto val=[&](char c)->int{ if('0'<=c&&c<='9')return c-'0'; if('a'<=c&&c<='z')return c-'a'+10; if('A'<=c&&c<='Z')return c-'A'+10; return 0; };
    for(size_t i=0;i<outlen;i++){
        out[i] = (uint8_t)((val(hex[2*i])<<4) | val(hex[2*i+1]));
    }
}

static void print_hex_be(const uint8_t* b, size_t n){
    for(size_t i=0;i<n;i++) std::printf("%02x", b[i]);
}

static int be_cmp(const uint8_t* a, const uint8_t* b){ // memcmp in big-endian space
    for(int i=0;i<32;i++){ int d = (int)a[i] - (int)b[i]; if(d) return d; }
    return 0;
}

int main(int argc, char** argv){
    // Defaults from your params
    uint32_t nTime = 1762086000;
    uint32_t nBits = 0x1e0ffff0;
    uint32_t nVersion = 4;
    std::string merkle_hex = "f1f855c804e50fd723eef2bbbb577c41f8cc172ce15e97096cde3cc00bbfc747";
    uint32_t start=0, stride=1;
    int threads = (int)std::max(1u, std::thread::hardware_concurrency());

    // Parse CLI
    for(int i=1;i<argc;i++){
        if(!std::strcmp(argv[i],"--time") && i+1<argc) nTime = std::strtoul(argv[++i],nullptr,0);
        else if(!std::strcmp(argv[i],"--bits") && i+1<argc) nBits = std::strtoul(argv[++i],nullptr,0);
        else if(!std::strcmp(argv[i],"--version") && i+1<argc) nVersion = std::strtoul(argv[++i],nullptr,0);
        else if(!std::strcmp(argv[i],"--merkle") && i+1<argc) merkle_hex = argv[++i];
        else if(!std::strcmp(argv[i],"--threads") && i+1<argc) threads = std::atoi(argv[++i]);
        else if(!std::strcmp(argv[i],"--start") && i+1<argc) start = (uint32_t)std::strtoul(argv[++i],nullptr,0);
        else if(!std::strcmp(argv[i],"--stride") && i+1<argc) stride = (uint32_t)std::strtoul(argv[++i],nullptr,0);
        else { std::fprintf(stderr,"Unknown arg: %s\n", argv[i]); return 1; }
    }

    uint8_t merkleLE[32]; { std::vector<uint8_t> tmp(32); hex2bin(merkle_hex.c_str(), tmp.data(), 32); for(int i=0;i<32;i++) merelyE: merkleLE[i]=tmp[31-i]; }

    // Precompute target from nBits
    uint8_t target[32] = {0};
    uint32_t exp = nBits >> 24;
    uint32_t mant= nBits & 0x00FFFFFF;
    if (exp<3 || exp>255){ std::fprintf(stderr,"Bad nBits\n"); return 1; }
    // place three mantissa bytes at positions exp-3..exp-1 (big-endian)
    target[exp-3] = (uint8_t)((mant >> 16) & 0xff);
    target[exp-2] = (uint8_t)((mant >>  8) & 0xff);
    target[exp-1] = (uint8_t)( mant        & 0xff);

    std::atomic<uint32_t> found(0);
    std::atomic<bool> done(false);
    uint8_t foundHash[32] = {0};

    // mining loop
    uint64_t total = 0;
    uint64_t t0 = GetTickCount64();
    #pragma omp parallel for schedule(static) num_threads( /* if openmp enabled */ 0 )
    for(int t=0; t<threads; ++t){
        uint8_t hdr[80] = {0};
        le32(&hdr[0], nVersion);
        // 32 bytes prevhash zero at [4..35]
        std::memcpy(&hdr[36], merkleLE, 32);
        le32(&hdr[68], nTime);
        le32(&hdr[72], nBits);

        uint32_t nonce = start + (uint32_t)t;
        while(!done.load(std::memory_order_relaxed)){
            le32(&hdr[76], nonce);
            uint8_t h[32]; sha256d(hdr, h);
            if (be_cmp(h, target) <= 0){
                if(!done.exchange(true)){
                    found.store(nonce);
                    std::memcpy(foundHash, h, 32);
                }
                break;
            }
            nonce += stride*threads;
            #pragma omp atomic
            total++;
            if(((nonce - (start + t)) & 0x7FFFFF) == 0){ // every ~8M per thread
                uint64_t dt = GetTickCount64() - t0;
                double mh = dt? (double)total / (double)dt : 0.0;
                #pragma omp critical
                std::fprintf(stderr, "[t%02d] scanned=%llu hash≈%.2f MH/s\r", t, (unsigned long long)total, mh);
            }
        }
    }

    if(!done.load()){
        std::fprintf(stderr,"\nNOT FOUND (try different --time or run longer)\n");
        return 2;
    }
    std::printf("\nFOUND nonce=%u\nHASH  = ", found.load());
    print_hex_be(foundHash, 32);
    std::printf("\nMERKLE= %s\nHDR   v=%u time=%u bits=%08X nonce=%u\n",
                merkle_hex.c_str(), nTime, nBits, nBits, found.load());

    return 0;
}
