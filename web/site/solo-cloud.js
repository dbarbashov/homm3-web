import * as db from "./solo-store.js";
const $ = (id) => document.getElementById(id),
  dialog = $("cloud-dialog");
let settings = await db.config(),
  mounted = false,
  syncing = false,
  scheduled,
  retry = 2000,
  problem = "",
  currentEngine;
let captureQueue = Promise.resolve();
const bases = new Map();
const solo = () =>
  !window.homm3Room &&
  !window.homm3Authority?.active &&
  location.hash !== "#replay-view";
const lock = (work) =>
  navigator.locks ? navigator.locks.request("homm3-solo-sync", work) : work();
async function engine() {
  return (currentEngine ||= fetch("/port/engine-build.json")
    .then((r) => {
      if (!r.ok) throw Error("Не удалось определить версию движка");
      return r.json();
    })
    .then((v) => v.engineRevision)
    .catch((e) => {
      currentEngine = null;
      throw e;
    }));
}
function message(text) {
  problem = text;
  render().catch(() => {});
}
async function request(
  path,
  method = "GET",
  body,
  credential = settings.token,
) {
  const controller = new AbortController(),
    timer = setTimeout(() => controller.abort(), 20000);
  try {
    const r = await fetch("/lobby/solo/" + path, {
      method,
      headers: {
        ...(credential ? { Authorization: "Bearer " + credential } : {}),
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      cache: "no-store",
    });
    if (!r.ok) {
      const v = await r.json().catch(() => ({}));
      const error = Error(
        v.error || "Облако временно недоступно. Сейвы остаются здесь.",
      );
      error.status = r.status;
      throw error;
    }
    return r;
  } finally {
    clearTimeout(timer);
  }
}
function encode(buffer) {
  let result = "";
  const a = new Uint8Array(buffer);
  for (let i = 0; i < a.length; i += 16384)
    result += String.fromCharCode(...a.subarray(i, i + 16384));
  return btoa(result);
}
function adopt(identity) {
  window.homm3Lobby?.adoptSoloIdentity(identity);
}
async function identity() {
  if (settings.owner) {
    const v = await (await request("identity", "POST")).json();
    if (v.owner !== settings.owner)
      throw Error("Изменился владелец облачной библиотеки");
    return;
  }
  let token = localStorage.getItem("homm3.session") || "",
    v;
  try {
    v = await (await request("identity", "POST", null, token)).json();
  } catch (e) {
    if (e.status !== 401 || !token) throw e;
    v = await (await request("identity", "POST", null, "")).json();
  }
  settings = { ...(await db.config()), ...v };
  await db.enroll(settings, true);
  adopt(v);
}
function snapshot(path) {
  if (!mounted || !solo()) return [];
  const selected =
    typeof path === "string"
      ? path.replaceAll("\\", "/").split("/").pop().toLowerCase()
      : null;
  return Module.FS.readdir("/runtime/games")
    .filter(
      (n) =>
        /\.gm[12]$/i.test(n) && (!selected || n.toLowerCase() === selected),
    )
    .map((name) => ({
      name,
      owner: settings.owner,
      data: Module.FS.readFile("/runtime/games/" + name).buffer,
    }));
}
async function capture(files, existing = false) {
  settings = await db.config();
  if (!settings.enabled || !solo()) return;
  const version = await engine(),
    tracked = await db.rows("files");
  for (const f of files) {
    if (
      existing &&
      !settings.importExisting &&
      !tracked.some((t) => t.owner === settings.owner && t.name === f.name) &&
      settings.excludedFiles?.[f.name] === (await db.hash(f.data))
    )
      continue;
    const owner = f.owner || settings.owner,
      base = bases.get(f.name);
    const row = await db.capture(
      owner,
      f.name,
      f.data,
      version,
      base && (!base.owner || base.owner === owner) ? base : null,
    );
    bases.set(f.name, row);
  }
  schedule(0);
  await render();
}
function queueCapture(files, existing = false) {
  captureQueue = captureQueue
    .then(() => capture(files, existing))
    .catch((e) => message("Локальная очередь не записана: " + e.message));
  return captureQueue;
}
// Called synchronously from the save event so successive autosaves cannot mutate queued bytes.
window.homm3SoloSnapshot = (path) => (settings.enabled ? snapshot(path) : []);
window.addEventListener("homm3-save-persisted", (event) => {
  if (event.detail?.solo) queueCapture(event.detail.solo);
});
async function installCopies() {
  if (
    !settings.enabled ||
    !mounted ||
    !solo() ||
    (window.homm3Boot?.running &&
      !["main", "new"].includes(window.homm3PortDiagnostics?.screen))
  )
    return;
  const version = await engine();
  let files = await db.rows("files"),
    changed = false;
  const copies = (await db.rows("copies")).filter(
    (c) =>
      c.owner === settings.owner &&
      c.engine === version &&
      settings.heads?.some((h) => h.revision === c.revision),
  );
  for (const row of copies) {
    const installed = files.find(
      (f) => f.owner === row.owner && f.revision === row.revision,
    );
    if (
      installed &&
      Module.FS.analyzePath("/runtime/games/" + installed.name).exists &&
      (await db.hash(
        Module.FS.readFile("/runtime/games/" + installed.name),
      )) === row.hash
    )
      continue;
    const parents = files.filter(
      (f) => f.owner === row.owner && f.slot === row.slot,
    );
    let previous = parents.find((f) => f.revision === row.parent),
      name = previous?.name || row.name,
      path = "/runtime/games/" + name;
    if (Module.FS.analyzePath(path).exists) {
      const actual = await db.hash(Module.FS.readFile(path));
      if (actual === row.hash) {
        const item = {
          ...row,
          key: row.owner + ":" + name,
          name,
          data: undefined,
        };
        await db.track(item);
        files.push(item);
        bases.set(name, item);
        continue;
      }
      if (!previous || actual !== previous.hash) {
        name =
          "Cloud_" +
          row.slot.slice(0, 8) +
          "_" +
          row.revision.slice(0, 8) +
          row.name.slice(-4);
        path = "/runtime/games/" + name;
      }
    }
    // Verify again immediately before writing; JS may have yielded to a native save.
    if (
      Module.FS.analyzePath(path).exists &&
      (!previous || (await db.hash(Module.FS.readFile(path))) !== previous.hash)
    ) {
      name =
        "Cloud_" +
        row.slot.slice(0, 8) +
        "_" +
        row.revision.slice(0, 8) +
        row.name.slice(-4);
      path = "/runtime/games/" + name;
      if (
        Module.FS.analyzePath(path).exists &&
        (await db.hash(Module.FS.readFile(path))) !== row.hash
      ) {
        name = "Cloud_" + db.id().slice(0, 12) + row.name.slice(-4);
        path = "/runtime/games/" + name;
      }
    }
    Module.FS.writeFile(path, new Uint8Array(row.data));
    changed = true;
    const item = { ...row, key: row.owner + ":" + name, name, data: undefined };
    await db.track(item);
    files = files.filter((f) => f.key !== item.key);
    files.push(item);
    bases.set(name, item);
  }
  if (changed) await window.homm3PersistFiles();
}
window.homm3SoloMounted = async () => {
  mounted = true;
  try {
    settings = await db.config();
    if (
      settings.enabled &&
      !settings.importExisting &&
      !settings.excludedFiles
    ) {
      const excludedFiles = {};
      for (const f of snapshot()) excludedFiles[f.name] = await db.hash(f.data);
      settings = { ...settings, excludedFiles };
      await db.configure(settings);
    }
    for (const row of await db.rows("files")) {
      if (
        row.owner === settings.owner &&
        Module.FS.analyzePath("/runtime/games/" + row.name).exists &&
        (await db.hash(Module.FS.readFile("/runtime/games/" + row.name))) ===
          row.hash
      )
        bases.set(row.name, row);
    }
    if (settings.enabled) await queueCapture(snapshot(), true);
    await installCopies();
    schedule(0);
  } catch (e) {
    message(e.message);
  }
};
async function sync() {
  if (syncing) return;
  syncing = true;
  problem = "";
  await render();
  try {
    await lock(async () => {
      settings = await db.config();
      if (!settings.enabled) return;
      await identity();
      if (!settings.enabled) return;
      for (const row of await db.rows("queue")) {
        const current = await db.config();
        if (!current.enabled || current.owner !== settings.owner) return;
        if (row.owner !== settings.owner) continue;
        const { sequence, owner, bytes, ...body } = row;
        const reply = await (
          await request("saves", "POST", { ...body, data: encode(row.data) })
        ).json();
        if (reply.revision !== row.revision || reply.hash !== row.hash)
          throw Error("Сервер подтвердил другую версию");
        await db.acknowledge(sequence);
      }
      if (!(await db.config()).enabled) return;
      const library = await (await request("saves")).json();
      if (library.owner !== settings.owner)
        throw Error("Неверный владелец библиотеки");
      const cached = await db.rows("copies");
      for (const row of library.heads) {
        if (
          cached.some(
            (c) =>
              c.owner === settings.owner &&
              c.revision === row.revision &&
              c.hash === row.hash,
          )
        )
          continue;
        const data = await (
          await request("saves/" + row.revision)
        ).arrayBuffer();
        if (data.byteLength !== row.bytes || (await db.hash(data)) !== row.hash)
          throw Error(
            "Повреждённый сейв не загружен. Локальная копия сохранена.",
          );
        await db.saveCopy({ ...row, data, owner: settings.owner });
      }
      settings = {
        ...(await db.config()),
        heads: library.heads,
        lastSync: Date.now(),
      };
      await db.configure(settings);
      await installCopies();
      retry = 2000;
    });
  } catch (e) {
    problem =
      e.status === 401
        ? "Доступ отозван. Введите новый код. Неотправленные сейвы сохранены здесь."
        : navigator.onLine
          ? e.message
          : "Нет сети. Сейвы сохранены здесь и отправятся при подключении.";
    retry = Math.min(60000, retry * 2);
  } finally {
    syncing = false;
    await render();
    if (settings.enabled) schedule(problem ? retry : 30000);
  }
}
function schedule(delay) {
  clearTimeout(scheduled);
  scheduled = setTimeout(() => sync(), delay);
}
async function render() {
  const queued = (await db.rows("queue")).filter(
      (r) => !r.owner || r.owner === settings.owner,
    ),
    heads = settings.heads || [];
  $("cloud-enable").hidden = settings.enabled;
  $("cloud-disable").hidden = !settings.enabled;
  $("cloud-sync").hidden = !settings.enabled;
  $("cloud-device").hidden = !settings.enabled;
  $("cloud-status").textContent =
    problem ||
    (syncing
      ? "Синхронизация…"
      : !settings.enabled
        ? "Сейвы сохраняются только на этом устройстве."
        : queued.length
          ? `Сохранено здесь. Ожидают отправки: ${queued.length}.`
          : settings.lastSync
            ? "Сохранено в облаке · " +
              new Date(settings.lastSync).toLocaleTimeString("ru", {
                hour: "2-digit",
                minute: "2-digit",
              })
            : "Новые сейвы будут отправляться автоматически.");
  $("cloud-sync").disabled = syncing;
  const installedFiles = mounted ? await db.rows("files") : [];
  const list = $("cloud-list");
  list.replaceChildren();
  for (const row of heads) {
    const tr = document.createElement("tr"),
      td = document.createElement("td");
    td.textContent = row.name;
    const detail = document.createElement("small");
    const conflicts = heads.filter((h) => h.slot === row.slot).length;
    detail.textContent =
      (conflicts > 1 ? "Продолжение " + row.revision.slice(0, 8) + " · " : "") +
      new Date(row.created * 1000).toLocaleString("ru") +
      (row.engine !== (await engine()) ? " · другая версия движка" : "");
    td.append(document.createElement("br"), detail);
    const installed = installedFiles.find(
      (f) => f.owner === settings.owner && f.revision === row.revision,
    );
    if (installed && installed.name !== row.name) {
      const local = document.createElement("small");
      local.textContent = "В «Загрузить игру»: " + installed.name;
      td.append(document.createElement("br"), local);
    }
    tr.append(td);
    list.append(tr);
  }
  $("cloud-empty").hidden = !!heads.length;
  $("cloud-count").textContent = heads.length
    ? `В облаке: ${heads.length}`
    : "";
}
async function show() {
  await render();
  dialog.showModal();
  $("cloud-close").focus();
}
for (const key of ["cloud-open", "view-cloud"])
  $(key).onclick = () => show().catch((e) => message(e.message));
$("cloud-close").onclick = () => dialog.close();
dialog.addEventListener("close", () =>
  document.querySelector("#canvas")?.focus(),
);
$("cloud-enable").onclick = async () => {
  try {
    settings = { ...(await db.config()), enabled: true };
    await db.configure(settings);
    await queueCapture(snapshot(), true);
    schedule(0);
    await render();
  } catch (e) {
    message(e.message);
  }
};
$("cloud-disable").onclick = async () => {
  settings = { ...(await db.config()), enabled: false };
  await db.configure(settings);
  clearTimeout(scheduled);
  await render();
};
$("cloud-sync").onclick = () => sync();
$("cloud-code-create").onclick = async () => {
  try {
    await sync();
    if (problem) throw Error(problem);
    const v = await (await request("device/code", "POST")).json();
    $("cloud-code").value = v.code.match(/.{1,8}/g).join("-");
    $("cloud-issued").hidden = false;
    $("cloud-code-status").textContent =
      "Код действует 10 минут и используется один раз.";
  } catch (e) {
    message(e.message);
  }
};
$("cloud-copy").onclick = async () => {
  try {
    await navigator.clipboard.writeText($("cloud-code").value);
    $("cloud-code-status").textContent = "Код скопирован.";
  } catch {
    $("cloud-code").select();
  }
};
$("cloud-claim").onsubmit = async (event) => {
  event.preventDefault();
  if (window.homm3Boot?.running || window.homm3Room) {
    message("Завершите текущую игру перед переносом доступа.");
    return;
  }
  try {
    const code = $("cloud-input").value.replace(/[\s-]/g, "").toLowerCase();
    if (!/^[a-f0-9]{32}$/.test(code))
      throw Error("Введите весь одноразовый код.");
    await lock(async () => {
      const v = await (
        await request("device/claim", "POST", { code }, "")
      ).json();
      if (
        v.owner !== settings.owner &&
        (await db.rows("queue")).some(
          (r) => !r.owner || r.owner === settings.owner,
        )
      )
        throw Error(
          "Сначала отправьте ожидающие сейвы прежней библиотеки. Они остаются на устройстве.",
        );
      settings = { ...v, enabled: true, importExisting: false };
      await db.enroll(settings, false);
      bases.clear();
      adopt(v);
    });
    $("cloud-input").value = "";
    await sync();
  } catch (e) {
    message(e.message);
  }
};
$("cloud-revoke").onclick = async () => {
  try {
    await request("device/revoke", "POST");
    $("cloud-code").value = "";
    $("cloud-issued").hidden = true;
    message("Доступ остальных устройств отозван.");
  } catch (e) {
    message(e.message);
  }
};
window.addEventListener("online", () => schedule(0));
window.addEventListener("focus", () => {
  if (settings.enabled) schedule(0);
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && settings.enabled) schedule(0);
});
window.homm3Cloud = {
  sync,
  show,
  mounted: () => mounted,
  settled: () => captureQueue,
};
await render();
if (settings.enabled) schedule(0);
