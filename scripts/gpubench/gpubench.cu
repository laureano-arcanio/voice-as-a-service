// Microbenchmarks de una GPU: memoria propia y transferencias PCIe host<->GPU.
// Un solo device por corrida; imprime un JSON por stdout (lo arma gpubench.py).
// Sin dependencias fuera del toolkit de CUDA.
#include <cuda_runtime.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { \
    fprintf(stderr, "CUDA %s:%d: %s\n", __FILE__, __LINE__, cudaGetErrorString(e_)); exit(2); } } while (0)

// Cada kernel recorre el buffer con stride de grilla y accesos de 16 B (uint4).
__global__ void k_read(const uint4* __restrict__ a, size_t n, unsigned* out) {
    unsigned s = 0;
    for (size_t i = blockIdx.x * (size_t)blockDim.x + threadIdx.x; i < n; i += (size_t)gridDim.x * blockDim.x) {
        uint4 v = a[i]; s ^= v.x ^ v.y ^ v.z ^ v.w;
    }
    if (s == 0x9e3779b9u) *out = s;  // evita que el compilador elimine la lectura
}
__global__ void k_write(uint4* __restrict__ a, size_t n) {
    for (size_t i = blockIdx.x * (size_t)blockDim.x + threadIdx.x; i < n; i += (size_t)gridDim.x * blockDim.x)
        a[i] = make_uint4((unsigned)i, 1u, 2u, 3u);
}
__global__ void k_copy(const uint4* __restrict__ a, uint4* __restrict__ b, size_t n) {
    for (size_t i = blockIdx.x * (size_t)blockDim.x + threadIdx.x; i < n; i += (size_t)gridDim.x * blockDim.x)
        b[i] = a[i];
}
__global__ void k_empty() {}

static double now_s() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
static double median(std::vector<double> v) { std::sort(v.begin(), v.end()); return v[v.size() / 2]; }

// Mide fn() `iters` veces (tras 2 de calentamiento); devuelve segundos por corrida.
template <class F> static std::vector<double> timeit(F fn, int iters) {
    for (int i = 0; i < 2; i++) fn();
    CK(cudaDeviceSynchronize());
    std::vector<double> t;
    for (int i = 0; i < iters; i++) { double t0 = now_s(); fn(); CK(cudaDeviceSynchronize()); t.push_back(now_s() - t0); }
    return t;
}
struct Bw { double med, best; };
static Bw bw(const std::vector<double>& t, double bytes) {
    return { bytes / median(t) / 1e9, bytes / *std::min_element(t.begin(), t.end()) / 1e9 };
}
static void jbw(const char* k, Bw b, bool last = false) {
    printf("\"%s\":{\"med\":%.2f,\"best\":%.2f}%s", k, b.med, b.best, last ? "" : ",");
}

int main(int argc, char** argv) {
    int dev = 0, iters = 10; size_t size_mb = 256, mem_mb = 1024;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--device") && i + 1 < argc) dev = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--iters") && i + 1 < argc) iters = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--size-mb") && i + 1 < argc) size_mb = atol(argv[++i]);
        else if (!strcmp(argv[i], "--mem-mb") && i + 1 < argc) mem_mb = atol(argv[++i]);
    }
    CK(cudaSetDevice(dev));
    cudaDeviceProp p; CK(cudaGetDeviceProperties(&p, dev));
    int memclk = 0, bus = 0, l2 = 0, sms = 0;
    CK(cudaDeviceGetAttribute(&memclk, cudaDevAttrMemoryClockRate, dev));
    CK(cudaDeviceGetAttribute(&bus, cudaDevAttrGlobalMemoryBusWidth, dev));
    CK(cudaDeviceGetAttribute(&l2, cudaDevAttrL2CacheSize, dev));
    CK(cudaDeviceGetAttribute(&sms, cudaDevAttrMultiProcessorCount, dev));
    size_t freeb, totb; CK(cudaMemGetInfo(&freeb, &totb));

    // Los buffers de memoria son 3 (lectura, escritura y copia usan 2): que entren en lo libre.
    size_t mem_b = mem_mb << 20;
    while (mem_b * 2 + (64u << 20) > freeb && mem_b > (64u << 20)) mem_b >>= 1;
    size_t xfer_b = size_mb << 20;

    printf("{\"device\":%d,\"name\":\"%s\",\"cc\":\"%d.%d\",\"sms\":%d,\"mem_total_mib\":%zu,\"mem_free_mib\":%zu,"
           "\"mem_clock_khz\":%d,\"bus_bits\":%d,\"l2_kib\":%d,\"mem_buf_mib\":%zu,\"xfer_mib\":%zu,\"iters\":%d,",
           dev, p.name, p.major, p.minor, sms, totb >> 20, freeb >> 20, memclk, bus, l2 >> 10, mem_b >> 20, xfer_b >> 20, iters);

    // --- Memoria de la GPU ---
    {
        uint4 *a, *b; unsigned* o;
        CK(cudaMalloc(&a, mem_b)); CK(cudaMalloc(&b, mem_b)); CK(cudaMalloc(&o, 4));
        CK(cudaMemset(a, 1, mem_b)); CK(cudaMemset(b, 2, mem_b));
        size_t n = mem_b / sizeof(uint4); int blocks = sms * 16, thr = 256;
        // Calentamiento ~2 s: la GPU sube de estado de energia (relojes de SM y memoria) recien bajo carga.
        for (double t0 = now_s(); now_s() - t0 < 2.0;) { k_copy<<<blocks, thr>>>(a, b, n); CK(cudaDeviceSynchronize()); }
        printf("\"mem\":{");
        jbw("read", bw(timeit([&] { k_read<<<blocks, thr>>>(a, n, o); }, iters), (double)mem_b));
        jbw("write", bw(timeit([&] { k_write<<<blocks, thr>>>(a, n); }, iters), (double)mem_b));
        jbw("copy", bw(timeit([&] { k_copy<<<blocks, thr>>>(a, b, n); }, iters), 2.0 * mem_b));   // lee + escribe
        jbw("memcpy_d2d", bw(timeit([&] { CK(cudaMemcpyAsync(b, a, mem_b, cudaMemcpyDeviceToDevice)); }, iters), 2.0 * mem_b), true);
        printf("},");
        cudaFree(a); cudaFree(b); cudaFree(o);
    }

    // --- PCIe ---
    {
        void *d, *d2, *pin, *pin2, *pag; CK(cudaMalloc(&d, xfer_b));
        CK(cudaMalloc(&d2, xfer_b));
        CK(cudaMallocHost(&pin, xfer_b)); CK(cudaMallocHost(&pin2, xfer_b));
        pag = malloc(xfer_b); memset(pag, 1, xfer_b); memset(pin, 1, xfer_b); memset(pin2, 1, xfer_b);
        cudaStream_t s1, s2; CK(cudaStreamCreate(&s1)); CK(cudaStreamCreate(&s2));
        double B = (double)xfer_b;
        printf("\"pcie\":{");
        jbw("h2d_pinned", bw(timeit([&] { CK(cudaMemcpyAsync(d, pin, xfer_b, cudaMemcpyHostToDevice)); }, iters), B));
        jbw("d2h_pinned", bw(timeit([&] { CK(cudaMemcpyAsync(pin, d, xfer_b, cudaMemcpyDeviceToHost)); }, iters), B));
        jbw("h2d_pageable", bw(timeit([&] { CK(cudaMemcpy(d, pag, xfer_b, cudaMemcpyHostToDevice)); }, iters), B));
        jbw("d2h_pageable", bw(timeit([&] { CK(cudaMemcpy(pag, d, xfer_b, cudaMemcpyDeviceToHost)); }, iters), B));
        // Bidireccional: H2D y D2H a la vez; se suman los bytes de las dos direcciones.
        jbw("bidir_pinned", bw(timeit([&] {
            CK(cudaMemcpyAsync(d, pin, xfer_b, cudaMemcpyHostToDevice, s1));
            CK(cudaMemcpyAsync(pin2, d2, xfer_b, cudaMemcpyDeviceToHost, s2));
            CK(cudaStreamSynchronize(s1)); CK(cudaStreamSynchronize(s2));
        }, iters), 2 * B));

        // Barrido de tamanos (H2D pinned): muestra donde la latencia deja de dominar.
        printf("\"sweep_h2d_pinned\":[");
        const size_t sizes[] = {4u << 10, 64u << 10, 1u << 20, 16u << 20, 256u << 20};
        bool first = true;
        for (size_t sz : sizes) {
            if (sz > xfer_b) continue;
            int it = sz < (1u << 20) ? 200 : iters;
            Bw r = bw(timeit([&] { CK(cudaMemcpyAsync(d, pin, sz, cudaMemcpyHostToDevice)); }, it), (double)sz);
            printf("%s{\"kib\":%zu,\"gbs\":%.2f}", first ? "" : ",", sz >> 10, r.med); first = false;
        }
        printf("],");

        // Latencia de un pedido minimo (4 B, pinned) y de lanzar un kernel vacio, en microsegundos.
        auto lat = [&](auto fn) {
            for (int i = 0; i < 100; i++) fn();
            std::vector<double> t;
            for (int i = 0; i < 1000; i++) { double t0 = now_s(); fn(); t.push_back((now_s() - t0) * 1e6); }
            return median(t);
        };
        double l_h2d = lat([&] { CK(cudaMemcpy(d, pin, 4, cudaMemcpyHostToDevice)); });
        double l_d2h = lat([&] { CK(cudaMemcpy(pin, d, 4, cudaMemcpyDeviceToHost)); });
        double l_k = lat([&] { k_empty<<<1, 1>>>(); CK(cudaDeviceSynchronize()); });
        printf("\"lat_us\":{\"h2d_4b\":%.1f,\"d2h_4b\":%.1f,\"kernel_launch\":%.1f}", l_h2d, l_d2h, l_k);
        printf("}");
        cudaFree(d); cudaFree(d2); cudaFreeHost(pin); cudaFreeHost(pin2); free(pag);
    }
    printf("}\n");
    return 0;
}
