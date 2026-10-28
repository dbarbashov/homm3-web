// New-map lobby rows include a default SavedGameHeader. Heap reuse must not
// turn it into a campaign or make writer/reader disagree about the wire layout.
#include "game.h"
#include "abstractfile.h"
#include <sstream>
#include <cstdio>
#include <cstring>
#include <new>
#include <stdexcept>

struct HeaderStream : TAbstractFile {
    std::stringbuf bytes;
    int read(void* p, int n) override { return bytes.sgetn(static_cast<char*>(p), n); }
    int write(const void* p, int n) override { return bytes.sputn(static_cast<const char*>(p), n); }
};
static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
int main() {
    int checks = 0;
    std::string canonical[3];
    try {
        for (int poison : {0, 1, 2, 0x10, 0x55, 0xa5, 0xff}) {
            for (int mode = 0; mode < 3; ++mode) {
                alignas(SavedGameHeader) unsigned char memory[sizeof(SavedGameHeader)];
                memset(memory, poison, sizeof(memory));
                auto* header = new(memory) SavedGameHeader;
                if (mode) {
                    header->m_mapHeader.m_version = MAP_FORMAT_SHADOW_OF_DEATH;
                    header->m_mapHeader.m_size = 36;
                    header->m_mapHeader.m_isPlayable = 1;
                    header->m_mapHeader.m_mapName = "Network round trip";
                    header->m_fileName = "network.gm1";
                }
                if (mode == 2) {
                    header->m_campaignGame = true;
                    header->m_campaign.m_currentCampaign = 3;
                    header->m_campaign.m_campaignFilename = "campaign.h3c";
                }
                HeaderStream stream;
                require(header->save(&stream) == 0, "save header failed");
                // Equal output across allocator patterns also checks padding in
                // filename/compatibility buffers, without depending on ABI size.
                const std::string encoded = stream.bytes.str();
                if (poison == 0) canonical[mode] = encoded;
                const unsigned int marker = 0x12345678;
                stream.write(&marker, sizeof(marker));
                SavedGameHeader restored;
                require(restored.load(&stream) == 0, "load header failed");
                unsigned int tail = 0;
                require(stream.read(&tail, sizeof(tail)) == sizeof(tail) && tail == marker,
                        "reader consumed a different layout than writer");
                require(restored.m_campaignGame == (mode == 2), "campaign flag changed");
                require(restored.m_mapHeader.m_size == (mode ? 36 : 0), "map size changed");
                require(restored.m_fileName == (mode ? "network.gm1" : ""), "filename changed");
                if (mode == 2) {
                    require(restored.m_campaign.m_campaignFilename == "campaign.h3c" &&
                            restored.m_campaign.m_currentCampaign == 3, "campaign data changed");
                }
                require(encoded == canonical[mode], "allocator bytes leaked into the header");
                header->~SavedGameHeader();
                ++checks;
            }
        }
        printf("{\"passed\":true,\"checks\":%d,\"allocatorPatterns\":7,\"modes\":[\"empty lobby header\",\"ordinary save\",\"campaign save\"]}\n", checks);
        return 0;
    } catch (const std::exception& error) {
        fprintf(stderr, "Header check %d: %s\n", checks, error.what());
        return 1;
    }
}
