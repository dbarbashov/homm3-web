#pragma once
class advManager;
namespace Port { namespace Camera {
bool enabled();
bool intermediateFrame();
// Fill the original movement frame's time budget with intermediate map draws.
void animateStep(advManager& map, int fromX, int fromY, unsigned long deadline);
void traceFrame(int width, int height);
} }
