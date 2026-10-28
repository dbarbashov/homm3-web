#include "smooth_camera.h"
#include "advmgr.h"
#include "hd_view.h"
#include "kbwin.h"
#include "winmgr.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace {
bool interpolating = false;
struct FrameScope {
    bool previous = interpolating;
    FrameScope(bool intermediate) { interpolating = intermediate; }
    ~FrameScope() { interpolating = previous; }
};
}
namespace Port { namespace Camera {
bool enabled() {
#ifdef __EMSCRIPTEN__
    return EM_ASM_INT({return window.homm3SmoothCamera !== false;});
#else
    const char* value = std::getenv("HOMM3_SMOOTH_CAMERA");
    return !value || value[0] != '0';
#endif
}
bool intermediateFrame() { return interpolating; }
void animateStep(advManager& map, int fromX, int fromY, unsigned long deadline) {
    const int toX = map.m_scrollX, toY = map.m_scrollY;
    const unsigned long start = GameTime::get();
    const long remaining = GameTime::elapsed(deadline, start);
    const unsigned long duration = remaining > 0 ? remaining : 0;
    // The previous committed frame already shows the starting position.
    // Avoid redrawing it at every original animation boundary.
    unsigned long nextFrame = start + 16;
    for (;;) {
        if (GameTime::elapsed(nextFrame, deadline) > 0) nextFrame = deadline;
        GameTime::delayTil(nextFrame);
        const unsigned long elapsed = GameTime::get() - start;
        const bool finalFrame = !duration || elapsed >= duration;
        const double progress = finalFrame ? 1.0 : double(elapsed) / duration;
        map.m_scrollX = std::lround(fromX + (toX - fromX) * progress);
        map.m_scrollY = std::lround(fromY + (toY - fromY) * progress);
        {
            // Extra camera frames must not accelerate the hero's sprite or
            // advance its footstep-sound cycle. The original frame advances once.
            FrameScope frame(!finalFrame);
            map.completeDraw(0);
            g_windowManager->updateScreen(0, 8, HD::mapRight() + 8, HD::mapHeight());
        }
        if (finalFrame) break;
        nextFrame += 16;
        if (GameTime::isPast(nextFrame)) nextFrame = GameTime::get() + 1;
    }
}
void traceFrame(int width, int height) {
#ifdef __EMSCRIPTEN__
    if (!g_advManager || !g_advManager->m_heroMoving || width < HD::mapRight() || height < HD::mapHeight()) return;
    EM_ASM({const trace=window.homm3CameraTrace;if(Array.isArray(trace)){
        trace.push({at:performance.now(),x:$0,y:$1,originX:$2,originY:$3,heroFrame:$4,intermediate:!!$5});
        if(trace.length>2048)trace.shift();
    }},g_advManager->m_scrollX,g_advManager->m_scrollY,g_advManager->m_radarOrigin.m_x,
        g_advManager->m_radarOrigin.m_y,g_advManager->m_cursorFrameCount,interpolating);
#else
    (void)width; (void)height;
#endif
}
} }
