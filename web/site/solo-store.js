/* Durable upload queue, separate from native IDBFS saves and offline resources. */
let opened;
export const id = () => crypto.randomUUID().replaceAll("-", "");
export const hash = async (bytes) =>
  Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
export function database() {
  return (opened ||= new Promise((resolve, reject) => {
    const r = indexedDB.open("homm3-solo-cloud-v1", 1);
    r.onupgradeneeded = () => {
      const d = r.result;
      d.createObjectStore("meta");
      d.createObjectStore("files", { keyPath: "key" });
      d.createObjectStore("queue", {
        keyPath: "sequence",
        autoIncrement: true,
      });
      d.createObjectStore("copies", { keyPath: "revision" });
    };
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  }));
}
async function transaction(names, mode, work) {
  const d = await database();
  return new Promise((resolve, reject) => {
    const tx = d.transaction(names, mode);
    let result;
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || Error("Запись отменена"));
    try {
      work(tx, (value) => {
        result = value;
      });
    } catch (e) {
      tx.abort();
      reject(e);
    }
  });
}
export async function config() {
  return (
    (await transaction(["meta"], "readonly", (tx, done) => {
      const r = tx.objectStore("meta").get("config");
      r.onsuccess = () => done(r.result);
    })) || { enabled: false, owner: null, token: "", importExisting: true }
  );
}
export function configure(value) {
  return transaction(["meta"], "readwrite", (tx) =>
    tx.objectStore("meta").put(value, "config"),
  );
}
export function rows(name) {
  return transaction([name], "readonly", (tx, done) => {
    const r = tx.objectStore(name).getAll();
    r.onsuccess = () => done(r.result);
  });
}
export function saveCopy(row) {
  return transaction(["copies"], "readwrite", (tx) =>
    tx.objectStore("copies").put(row),
  );
}
export function track(row) {
  return transaction(["files"], "readwrite", (tx) =>
    tx.objectStore("files").put(row),
  );
}
export function acknowledge(sequence) {
  return transaction(["queue"], "readwrite", (tx) =>
    tx.objectStore("queue").delete(sequence),
  );
}
export async function capture(owner, name, data, engine, base) {
  const digest = await hash(data),
    revision = id();
  return transaction(["meta", "files", "queue"], "readwrite", (tx, done) => {
    // Enrollment and capture share this transaction boundary. A digest that
    // finishes after enrollment must not leave a permanently unowned upload.
    const configuration = tx.objectStore("meta").get("config");
    configuration.onsuccess = () => {
      const targetOwner = owner || configuration.result?.owner || null;
      const key = (targetOwner || "local") + ":" + name;
      const files = tx.objectStore("files"),
        request = files.get(key);
      request.onsuccess = () => {
        const old = request.result;
        if (old?.hash === digest) {
          done(old);
          return;
        }
        const row = {
          owner: targetOwner,
          slot: base?.slot || id(),
          revision,
          parent: base?.revision || null,
          name,
          engine,
          hash: digest,
          data,
          bytes: data.byteLength,
        };
        tx.objectStore("queue").add(row);
        files.put({ ...row, key, data: undefined });
        done({ ...row, data: undefined });
      };
    };
  });
}
// First enrollment may bind previously offline local work; changing accounts never does.
export function enroll(identity, first) {
  return transaction(["meta", "queue", "files"], "readwrite", (tx) => {
    tx.objectStore("meta").put(identity, "config");
    if (!first) return;
    for (const name of ["queue", "files"]) {
      const store = tx.objectStore(name),
        request = store.openCursor();
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return;
        const row = cursor.value;
        if (!row.owner) {
          row.owner = identity.owner;
          if (name === "files") {
            store.delete(row.key);
            row.key = identity.owner + ":" + row.name;
            store.put(row);
          } else cursor.update(row);
        }
        cursor.continue();
      };
    }
  });
}
