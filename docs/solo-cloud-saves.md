# Single-player cloud saves

Open **Single player → Cloud saves → Enable synchronization** once. Normal saves
and autosaves are written locally first, then uploaded automatically. This is
optional: single-player continues to run locally, including without a connection.
Game installation files are not uploaded. Existing local saves can upload before
you start the game; there is no need to create a new party first. An empty cloud
library is reported explicitly.

## Continue on another device

1. In **Cloud saves → Continue on another device**, generate a one-use code.
2. Open Cloud saves on the second device and enter that code within ten minutes.
   You can do this before launch or from the original game’s main menu. The
   result appears next to the code field. A running adventure/battle is protected;
   return to the game’s main menu before changing its library.
3. Prepare your game resources there, start the game and use its normal **Load
   game** menu. Downloaded saves appear there automatically.

Each device keeps its own access credential. Both can play single-player without
interrupting each other. **Forget other devices** revokes the other credentials;
unsent progress stays on those devices until access is restored with a new code.
Keep codes private. Clearing all browser storage removes local credentials and
local files; a linked device can issue another code.

## Offline play and conflicts

Install the game for offline use first if you want to reopen it without a network.
The upload queue survives page/browser closure. Uploads retry when the application
opens, reconnects or returns to the foreground. Closing the browser does not
promise a background upload. Another device only receives completed uploads.

Two devices or tabs can continue the same save independently. Both versions are
kept, with separate files where names collide. Choose the continuation through
Load game; worlds are never merged and timestamps never decide a winner. Cloud
sync does not replace an adventure or battle currently running on the client.
Newly received saves are installed before game launch or at the main menu.

## Current limits

- This synchronizes `.GM1`/`.GM2` files, including native autosaves. It does not
  preserve an unsaved current decision or resume an unfinished single-player battle.
- Downloads are installed only for the exact engine revision that created them.
  A different revision is marked in the library and retained in cloud storage.
- Limits are 8 MiB per save, 256 MiB and 1,024 immutable revisions per library.
  A full cloud library leaves further uploads queued locally and shows an error.
  Automatic retention and cloud deletion are not available in this first version.
- Deleting a local file does not delete its cloud copy. Disable synchronization
  to stop transfers; this preserves local saves, pending uploads and cloud copies.

Multiplayer, replay and training sessions do not create solo cloud saves.
