# Saved games, replay and training

Server-hosted games keep their history after leaving the room or closing the
browser. Refreshing the game resumes the current state. **Main menu → Home**
leaves the active session; **Multiplayer → My games → Continue** returns later.
The saved-game row shows the last saved day, current player and update time.

## Continue on another device

Open **Access on another device** in the multiplayer browser. On your existing
device, create and copy a code. Enter it on the new device, then select the game
in **My games**. The code is valid for ten minutes and can be used once. Joining
from another device disconnects the old active session without deleting the game.
Up to eight devices can retain access. **Forget other devices** revokes the other
credentials and any outstanding transfer code. Keep access codes private.

## Replay a bug or review your game

A bug-report link opens the native game renderer at the captured moment. Use the
slider, arrows or Play to step through recorded decision boundaries. Opening a
recording does not send commands to the original game. The view is limited to the
player whose report was captured. **Report a bug** opens the GitHub issue form
with the recording link attached. **My games → Review** creates a fresh recording.
If resources are not configured, choose your installation with **Game files** in
the viewer. Files stay in browser memory and remain available while seeking;
they are never uploaded with the report.

Playback reconstructs game states and pending choices. It is not a video of the
original pointer, exact animation timing or original audio stream. The separate
parity harness records frames, sounds and timing for presentation regressions.

## Try another continuation

At a supported point in your own turn, **Play differently** creates a separate
training game. You keep your seat and control your decisions, including battles;
original AI controls the other seats. The source game and its report remain
unchanged. A public report link alone does not grant permission to create a branch:
you must use the device credentials of that seat. Older engine versions may not
support training branches.

## Recovery boundaries

Each match pins its map, setup, random seed and compatible engine version. The
server verifies its command journal during recovery. Native checkpoints accelerate
restoration at safe adventure boundaries; a pending battle is reconstructed from
the preceding checkpoint and the journal tail, then opened at its current choice.
Up to eight recent checkpoints are retained. Removing older checkpoints does not
remove the journal or invalidate pinned reports. Saved games and pinned reports
are not automatically deleted by an idle-room cleanup.

These features apply to server-hosted games. Legacy peer games retain their
existing behavior.
