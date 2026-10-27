#pragma once
#include <cstddef>
#include <cstdio>
namespace Port {
// Archives are immutable while open; close invalidates every cached member.
bool readCompressedLod(FILE* file, long offset, unsigned char* output, size_t size, size_t packedSize);
void forgetLod(FILE* file);
struct LodCacheStats {size_t bytes, entries, hits, misses;};
LodCacheStats lodCacheStats();
}
