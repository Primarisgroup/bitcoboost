#include <stdint.h>
#include <stdio.h>
#include <string>
#include <cuda_runtime.h>

#define CUDA_CHECK(x) do{ cudaError_t e=(x); if(e!=cudaSuccess){ \
  printf("CUDA_ERROR: %s at %s:%d\n", cudaGetErrorString(e), __FILE__, __LINE__); return 9; } }while(0)

__device__ __forceinline__ uint32_t R(uint32_t x,int n){ return (x>>n)|(x<<(32-n)); }
__device__ __forceinline__ uint32_t Ch(uint32_t x,uint32_t y,uint32_t z){ return (x & y) ^ (~x & z); }
__device__ __forceinline__ uint32_t Maj(uint32_t x,uint32_t y,uint32_t z){ return (x & y) ^ (x & z) ^ (y & z); }
__device__ __forceinline__ uint32_t S0(uint32_t x){ return R(x,2)^R(x,13)^R(x,22); }
__device__ __forceinline__ uint32_t S1(uint32_t x){ return R(x,6)^R(x,11)^R(x,25); }
__device__ __forceinline__ uint32_t s0(uint32_t x){ return R(x,7)^R(x,18)^(x>>3); }
__device__ __forceinline__ uint32_t s1(uint32_t x){ return R(x,17)^R(x,19)^(x>>10); }
__constant__ uint32_t Kc[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};

__device__ void sha256_block(const uint8_t* data, uint32_t H[8]){
  uint32_t w[64];
  #pragma unroll
  for(int i=0;i<16;i++){ w[i]=(data[4*i]<<24)|(data[4*i+1]<<16)|(data[4*i+2]<<8)|data[4*i+3]; }
  #pragma unroll
  for(int i=16;i<64;i++){ w[i]=s1(w[i-2])+w[i-7]+s0(w[i-15])+w[i-16]; }
  uint32_t a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
  #pragma unroll
  for(int i=0;i<64;i++){
    uint32_t t1=h+S1(e)+Ch(e,f,g)+Kc[i]+w[i];
    uint32_t t2=S0(a)+Maj(a,b,c);
    h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
  }
  H[0]+=a; H[1]+=b; H[2]+=c; H[3]+=d; H[4]+=e; H[5]+=f; H[6]+=g; H[7]+=h;
}
__device__ void sha256d_header80(const uint8_t hdr[80], uint8_t out[32]){
  uint32_t H[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
  uint8_t b1[64],b2[64]={0};
  for(int i=0;i<64;i++) b1[i]=hdr[i]; sha256_block(b1,H);
  for(int i=0;i<16;i++) b2[i]=hdr[64+i]; b2[16]=0x80; for(int i=17;i<56;i++) b2[i]=0; uint64_t bl=80ull*8ull;
  for(int i=0;i<8;i++) b2[56+i]=(uint8_t)((bl>>(56-8*i))&0xff); sha256_block(b2,H);
  uint8_t b3[64]={0}; for(int i=0;i<32;i++) b3[i]=(uint8_t)((H[i/4]>>(24-8*(i%4)))&0xff); b3[32]=0x80; uint64_t bl2=32ull*8ull;
  for(int i=0;i<8;i++) b3[56+i]=(uint8_t)((bl2>>(56-8*i))&0xff);
  uint32_t H2[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
  sha256_block(b3,H2);
  for(int i=0;i<32;i++) out[i]=(uint8_t)((H2[i/4]>>(24-8*(i%4)))&0xff);
}

// FIX big-endian corretto del target da compact "bits"
__device__ void bits_to_target(uint32_t bits, uint8_t T[32]){
  for(int i=0;i<32;i++) T[i]=0;
  uint32_t exp = bits >> 24;          // esponente (numero di byte)
  uint32_t mant = bits & 0x007fffff;  // mantissa (3 byte)
  if (exp <= 3){
    uint32_t v = mant >> (8*(3-exp));
    T[29] = (v >> 16) & 0xff;
    T[30] = (v >> 8)  & 0xff;
    T[31] =  v        & 0xff;
  } else {
    int start = 32 - (int)exp;        // posizione MSB in buffer BE
    if (start >= 0 && start+2 < 32){
      T[start+0] = (mant >> 16) & 0xff;
      T[start+1] = (mant >> 8)  & 0xff;
      T[start+2] =  mant        & 0xff;
    }
  }
}
__device__ bool leq_be(const uint8_t h[32],const uint8_t t[32]){
  #pragma unroll
  for(int i=0;i<32;i++){ if(h[i]<t[i]) return true; if(h[i]>t[i]) return false; } return true;
}
struct Params{ uint32_t ver; uint8_t prev[32]; uint8_t mrkl[32]; uint32_t time; uint32_t bits; uint32_t start; };

__global__ void mine_kernel(Params p, uint32_t* found, int* flag){
  if(*flag) return;
  uint32_t gid=blockIdx.x*blockDim.x+threadIdx.x;
  uint32_t nonce=p.start+gid; uint8_t hdr[80];
  hdr[0]=p.ver&0xff; hdr[1]=p.ver>>8; hdr[2]=p.ver>>16; hdr[3]=p.ver>>24;
  for(int i=0;i<32;i++){ hdr[4+i]=p.prev[i]; hdr[36+i]=p.mrkl[i]; }
  hdr[68]=p.time&0xff; hdr[69]=p.time>>8; hdr[70]=p.time>>16; hdr[71]=p.time>>24;
  hdr[72]=p.bits&0xff; hdr[73]=p.bits>>8; hdr[74]=p.bits>>16; hdr[75]=p.bits>>24;
  hdr[76]=nonce&0xff; hdr[77]=nonce>>8; hdr[78]=nonce>>16; hdr[79]=nonce>>24;
  uint8_t out[32],T[32]; sha256d_header80(hdr,out); bits_to_target(p.bits,T);
  if(leq_be(out,T)){ if(atomicCAS(flag,0,1)==0){ *found=nonce; } }
}

static inline uint8_t hexv(char c){ if(c>='0'&&c<='9')return c-'0'; if(c>='a'&&c<='f')return 10+c-'a'; if(c>='A'&&c<='F')return 10+c-'A'; return 0; }
static bool hex32_be_to_le(const std::string& s, uint8_t out[32]){
  if(s.size()!=64) return false; uint8_t be[32];
  for(int i=0;i<32;i++){ be[i]=(hexv(s[2*i])<<4)|hexv(s[2*i+1]); }
  for(int i=0;i<32;i++) out[i]=be[31-i]; return true;
}

int main(int argc,char**argv){
  int dev=0; int ndev=0; CUDA_CHECK(cudaGetDeviceCount(&ndev)); if(ndev<1){ printf("CUDA_ERROR: no device\n"); return 8; }
  CUDA_CHECK(cudaSetDevice(dev));
  cudaDeviceProp prop; CUDA_CHECK(cudaGetDeviceProperties(&prop,dev));
  printf("CUDA device: %s, CC %d.%d\n", prop.name, prop.major, prop.minor);

  std::string merkle=""; uint32_t ver=4; uint32_t time=0; uint32_t bits=0x207fffff; uint32_t start=0;
  for(int i=1;i<argc;i++){
    std::string a=argv[i];
    if(a=="--merkle" && i+1<argc){ merkle=argv[++i]; }
    else if(a=="--time" && i+1<argc){ time=(uint32_t)strtoul(argv[++i],nullptr,10); }
    else if(a=="--bits" && i+1<argc){ bits=(uint32_t)strtoul(argv[++i],nullptr,16); }
    else if(a=="--version" && i+1<argc){ ver=(uint32_t)strtoul(argv[++i],nullptr,10); }
    else if(a=="--start" && i+1<argc){ start=(uint32_t)strtoul(argv[++i],nullptr,10); }
  }
  if(merkle.empty() || time==0){
    printf("usage: bb_gen_cuda.exe --merkle <64hex_BE> --time <unix> --bits <hex> --version <int> [--start N]\n");
    return 1;
  }

  uint8_t prev[32]={0}, mrkl[32]; if(!hex32_be_to_le(merkle,mrkl)){ printf("bad merkle\n"); return 2; }
  Params h{ver,{0},{0},time,bits,start}; for(int i=0;i<32;i++){ h.prev[i]=prev[i]; h.mrkl[i]=mrkl[i]; }
  Params *d; uint32_t *dnonce; int *dflag;
  CUDA_CHECK(cudaMalloc(&d,sizeof(Params)));
  CUDA_CHECK(cudaMalloc(&dnonce,sizeof(uint32_t)));
  CUDA_CHECK(cudaMalloc(&dflag,sizeof(int)));
  CUDA_CHECK(cudaMemcpy(d,&h,sizeof(Params),cudaMemcpyHostToDevice));
  int z=0; CUDA_CHECK(cudaMemcpy(dflag,&z,sizeof(int),cudaMemcpyHostToDevice));

  dim3 blk(256), grid(65535); // ~16.7M nonce
  mine_kernel<<<grid,blk>>>(*d,dnonce,dflag);
  cudaError_t ke=cudaGetLastError(); if(ke!=cudaSuccess){ printf("KERNEL_LAUNCH_ERROR: %s\n", cudaGetErrorString(ke)); return 10; }
  CUDA_CHECK(cudaDeviceSynchronize());

  int found=0; CUDA_CHECK(cudaMemcpy(&found,dflag,sizeof(int),cudaMemcpyDeviceToHost));
  if(found){
    uint32_t nonce=0; CUDA_CHECK(cudaMemcpy(&nonce,dnonce,sizeof(uint32_t),cudaMemcpyDeviceToHost));
    printf("FOUND nonce=%u (0x%08x)\n", nonce, nonce);
  } else {
    printf("NOTFOUND (start=%u, count=%u)\n", start, 65535*256);
  }
  cudaFree(d); cudaFree(dnonce); cudaFree(dflag);
  return 0;
}
