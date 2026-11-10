// manus_pair: list Manus dongles/gloves and pair gloves that are in pairing mode (LED blinking white)
// to the connected dongle, using the Manus SDK in Integrated mode (no MANUS Core needed).
//
// Sharpa's Linux tools (SharpaManusClient, CalibrationGUI) have no pairing step; on Windows this is
// the "Pair" button in the MANUS Core dashboard. This calls CoreSdk_PairGloveToDongle instead.
//
//   ./manus_pair            # pair every glove that is Unpaired/Pairing; stops when all seen gloves are paired (max 60 s)
//   ./manus_pair --list     # only print what the SDK sees, never pair
//   ./manus_pair --seconds 120
//
// Close SharpaManusClient.out / CalibrationGUI.out first: only one Integrated instance may own the dongle.
// Build: make (or bash scripts/setup_teleop.sh). Run: bash scripts/teleop.sh pair [--list]
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <thread>

#include "ManusSDK.h"

static std::mutex g_Mutex;
static std::unique_ptr<Landscape> g_Landscape;
static std::atomic<bool> g_HaveLandscape{false};

static void OnLandscape(const Landscape* const p_Landscape)
{
    std::lock_guard<std::mutex> lock(g_Mutex);
    std::memcpy(g_Landscape.get(), p_Landscape, sizeof(Landscape));
    g_HaveLandscape = true;
}

static void OnSystem(const SystemMessage* const p_Msg)
{
    if (p_Msg->type == SystemMessageType_SessionRefusedDueToLicenseIssue)
        std::printf("!! SYSTEM: session refused due to LICENSE issue: %s\n", p_Msg->infoString);
}

static const char* SideName(Side s) { return s == Side_Left ? "LEFT" : s == Side_Right ? "RIGHT" : "?"; }
static const char* PairName(DevicePairedState p)
{
    switch (p) {
        case DevicePairedState_Paired: return "Paired";
        case DevicePairedState_Unpaired: return "Unpaired";
        case DevicePairedState_Pairing: return "Pairing";
        default: return "Unknown";
    }
}
static const char* FamilyName(DeviceFamilyType f)
{
    switch (f) {
        case DeviceFamilyType_MetaglovePro: return "MetaglovePro";
        case DeviceFamilyType_MetagloveProPrecision: return "MetaGloveProPrecision";
        case DeviceFamilyType_Metaglove: return "Metaglove";
        case DeviceFamilyType_Prime3: return "Prime3";
        default: return "other";
    }
}

int main(int argc, char** argv)
{
    bool listOnly = false;
    int seconds = 60;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--list") listOnly = true;
        else if (a == "--seconds" && i + 1 < argc) seconds = std::atoi(argv[++i]);
        else { std::printf("usage: %s [--list] [--seconds N]\n", argv[0]); return 2; }
    }
    g_Landscape = std::make_unique<Landscape>();

    if (CoreSdk_InitializeIntegrated() != SDKReturnCode_Success) { std::printf("InitializeIntegrated failed\n"); return 1; }
    CoreSdk_RegisterCallbackForLandscapeStream(OnLandscape);
    CoreSdk_RegisterCallbackForSystemStream(OnSystem);
    CoordinateSystemVUH vuh;
    CoordinateSystemVUH_Init(&vuh);
    vuh.handedness = Side_Right; vuh.up = AxisPolarity_PositiveZ; vuh.view = AxisView_XFromViewer; vuh.unitScale = 1.0f;
    CoreSdk_InitializeCoordinateSystemWithVUH(vuh, true);
    // Same connect sequence as SharpaManusClient (Integrated mode still exposes a local "host").
    for (int tries = 0;; ++tries) {
        uint32_t n = 0;
        if (CoreSdk_LookForHosts(1, false) == SDKReturnCode_Success &&
            CoreSdk_GetNumberOfAvailableHostsFound(&n) == SDKReturnCode_Success && n > 0) {
            std::unique_ptr<ManusHost[]> hosts(new ManusHost[n]);
            if (CoreSdk_GetAvailableHostsFound(hosts.get(), n) == SDKReturnCode_Success &&
                CoreSdk_ConnectToHost(hosts[0]) != SDKReturnCode_NotConnected) break;
        }
        if (tries >= 10) { std::printf("Could not connect to the integrated host\n"); CoreSdk_ShutDown(); return 1; }
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }

    std::printf("manus_pair: %s, up to %d s. Put each glove in pairing mode (LED blinking white).\n",
                listOnly ? "LIST ONLY" : "will PAIR gloves in Unpaired/Pairing state", seconds);
    std::set<uint32_t> attempted;
    std::string lastSummary;
    int pairedSeen = 0;
    uint32_t donglesSeen = 0;
    auto t0 = std::chrono::steady_clock::now();
    while (std::chrono::steady_clock::now() - t0 < std::chrono::seconds(seconds)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
        if (!g_HaveLandscape) { std::printf("  ... waiting for device landscape\n"); continue; }
        static std::unique_ptr<Landscape> L = std::make_unique<Landscape>();
        { std::lock_guard<std::mutex> lock(g_Mutex); std::memcpy(L.get(), g_Landscape.get(), sizeof(Landscape)); }
        const DeviceLandscape& D = L->gloveDevices;
        donglesSeen = D.dongleCount;

        char buf[512];
        std::string summary;
        for (uint32_t i = 0; i < D.dongleCount; ++i) {
            const DongleLandscapeData& d = D.dongles[i];
            std::snprintf(buf, sizeof buf, "  dongle 0x%08X  family=%s  license='%s'  left=0x%08X right=0x%08X\n",
                          d.id, FamilyName(d.familyType), d.licenseType, d.leftGloveID, d.rightGloveID);
            summary += buf;
        }
        pairedSeen = 0;
        for (uint32_t i = 0; i < D.gloveCount; ++i) {
            const GloveLandscapeData& g = D.gloves[i];
            if (g.pairedState == DevicePairedState_Paired) ++pairedSeen;
            std::snprintf(buf, sizeof buf, "  glove  0x%08X  %-5s %-12s state=%-8s dongle=0x%08X battery=%u%% signal=%d\n",
                          g.id, SideName(g.side), FamilyName(g.familyType), PairName(g.pairedState), g.dongleID,
                          g.batteryPercentage, g.transmissionStrength);
            summary += buf;
        }
        if (summary != lastSummary) {
            std::printf("[%3llds] dongles=%u gloves=%u\n%s", (long long)std::chrono::duration_cast<std::chrono::seconds>(
                            std::chrono::steady_clock::now() - t0).count(), D.dongleCount, D.gloveCount, summary.c_str());
            lastSummary = summary;
        }
        if (listOnly) continue;
        for (uint32_t i = 0; i < D.gloveCount; ++i) {
            const GloveLandscapeData& g = D.gloves[i];
            bool needs = g.pairedState == DevicePairedState_Unpaired || g.pairedState == DevicePairedState_Pairing;
            if (!needs || attempted.count(g.id) || D.dongleCount == 0) continue;
            attempted.insert(g.id);
            bool ok = false;
            SDKReturnCode rc = (D.dongleCount == 1) ? CoreSdk_PairGloveToDongle(g.id, D.dongles[0].id, &ok)
                                                    : CoreSdk_PairGlove(g.id, &ok);
            std::printf(">> pair glove 0x%08X (%s) -> %s: rc=%d result=%s\n", g.id, SideName(g.side),
                        D.dongleCount == 1 ? "dongle" : "first free dongle", (int)rc, ok ? "true" : "false");
        }
        if (!listOnly && D.gloveCount > 0 && pairedSeen == (int)D.gloveCount) {
            std::printf("All %u glove(s) paired.\n", D.gloveCount);
            break;
        }
    }
    if (donglesSeen == 0)
        std::printf("No Manus dongle found. Plugged in? udev rule installed (scripts/install_teleop_deps.sh)?\n");
    std::printf("Done: %d glove(s) in Paired state. Shutting down SDK ...\n", pairedSeen);
    CoreSdk_ShutDown();
    return 0;
}
