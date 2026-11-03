# Solo save synchronization protocol

All endpoints are under `/lobby/solo`. Credentials use `Authorization: Bearer
<device-token>`; never put them in URLs. Responses are private and non-cacheable.
Saves are opaque, already-compressed native files, not render projections.

| Method and path | Purpose |
| --- | --- |
| POST `identity` | Enroll the existing device credential or create an owner when no credential is supplied. Return `owner`, `token`, `name`. An invalid supplied token is never silently replaced. |
| POST `device/code` | Issue a one-use ten-minute transfer code. |
| POST `device/claim` | Exchange `{code}` for another credential belonging to the same owner. |
| POST `device/revoke` | Retain this credential and revoke the owner's others and outstanding codes. |
| GET `saves` | Return `{owner, heads}`: current leaves of each slot's revision graph. |
| POST `saves` | Commit an immutable revision and return its metadata after durable publication. |
| GET `saves/{revision}` | Download the authenticated owner's verified bytes. |

Upload JSON contains `slot`, `revision` (random 32-character lowercase hex IDs),
`parent` (nullable revision ID), `name`, `engine` (40-character commit), `hash`
(SHA-256) and `data` (base64). Metadata replaces data with `bytes` and `created`
(server Unix seconds). A parent must already exist in the same slot. A stale
known parent is accepted as another branch. Exact retries return the original
revision; reuse of an ID for different content is rejected.

The client snapshots changed file bytes at the native save event, waits for local
IDBFS persistence, then transactionally writes its own IndexedDB queue and file
metadata. Startup reconciles local files to recover interrupted enqueue work.
Each tab retains the baseline it actually loaded; a shared metadata store must
not fabricate ancestry between independent native worlds. Uploads drain in order.
Queue entries are removed only after the exact revision and hash are acknowledged.
Downloads are verified before caching and installed without overwriting changed
local files. Different engine versions are retained without automatic loading.

Missing/revoked credentials return 401; inaccessible revisions return 404;
validation/quota failures return 422; concurrency/rate limits return 429. Queued
local work survives these errors. Request bodies are bounded at 12 MiB; decoded
files at 8 MiB. There are at most four simultaneous requests and sixteen anonymous
identity enrollments per minute per service process. Ownership is checked before
reading a protected request body. No game simulation process is needed for file
synchronization.
