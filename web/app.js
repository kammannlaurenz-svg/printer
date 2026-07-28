"use strict";

const { SUPABASE_URL, SUPABASE_KEY } = window.CONFIG;
const REST = `${SUPABASE_URL}/rest/v1`;
const HEADERS = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
  "Content-Type": "application/json",
};

let currentUser = "";
let imageDataUrl = "";
let imageName = "";

// ---------- Hilfen ----------
function $(id) { return document.getElementById(id); }

function setStatus(el, msg, kind) {
  el.textContent = msg;
  el.className = "status" + (kind ? " " + kind : "");
}

// ---------- Login ----------
async function login() {
  const name = $("username").value.trim();
  const pw = $("password").value;
  const st = $("loginStatus");

  if (!name) return setStatus(st, "Bitte Namen eingeben.", "err");
  if (!pw) return setStatus(st, "Bitte Passwort eingeben.", "err");

  setStatus(st, "Prüfe…", "");
  $("loginBtn").disabled = true;

  try {
    const r = await fetch(`${REST}/rpc/verify_web_password`, {
      method: "POST",
      headers: HEADERS,
      body: JSON.stringify({ pw }),
    });
    const ok = await r.json();
    if (ok === true) {
      currentUser = name;
      localStorage.setItem("druck_user", name);
      $("password").value = "";
      setStatus(st, "", "");
      openApp();
    } else {
      setStatus(st, "Falsches Passwort.", "err");
    }
  } catch (e) {
    setStatus(st, "Fehler bei der Anmeldung: " + e.message, "err");
  } finally {
    $("loginBtn").disabled = false;
  }
}

function logout() {
  localStorage.removeItem("druck_user");
  currentUser = "";
  $("appView").hidden = true;
  $("loginView").hidden = false;
}

function openApp() {
  $("loginView").hidden = true;
  $("appView").hidden = false;
  $("showUser").textContent = currentUser;
  if (!$("listItems").children.length) {
    addItem();
    addItem();
  }
}

// ---------- Tabs ----------
function showTab(which) {
  for (const t of ["text", "list", "image"]) {
    $("page" + cap(t)).classList.toggle("active", t === which);
    $("tab" + cap(t)).classList.toggle("active", t === which);
  }
}
function cap(s) { return s[0].toUpperCase() + s.slice(1); }

// ---------- Senden: Text ----------
async function sendText() {
  const text = $("text").value.trim();
  const st = $("textStatus");
  if (!text) return setStatus(st, "Bitte Text eingeben.", "err");

  setStatus(st, "Sende…", "");
  $("sendTextBtn").disabled = true;
  try {
    await createJob({ type: "text", text: "[BOX]Notiz\n" + text, username: currentUser, status: "pending" });
    $("text").value = "";
    setStatus(st, "Gesendet ✅", "ok");
  } catch (e) {
    setStatus(st, "Fehler: " + e.message, "err");
  } finally {
    $("sendTextBtn").disabled = false;
  }
}

// ---------- Liste ----------
let listMode = "list"; // "list" | "todo"

function setListMode(mode) {
  listMode = mode;
  $("modeList").classList.toggle("active", mode === "list");
  $("modeTodo").classList.toggle("active", mode === "todo");
  renderBon();
}

function addItem(value = "") {
  const row = document.createElement("div");
  row.className = "item";
  const input = document.createElement("input");
  input.placeholder = "Eintrag…";
  input.value = value;
  input.addEventListener("input", renderBon);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addItem();
    }
  });
  const del = document.createElement("button");
  del.type = "button";
  del.className = "del";
  del.textContent = "✕";
  del.onclick = () => { row.remove(); renderBon(); };
  row.appendChild(input);
  row.appendChild(del);
  $("listItems").appendChild(row);
  input.focus();
  renderBon();
}

function getItems() {
  return [...$("listItems").querySelectorAll("input")]
    .map((i) => i.value.trim())
    .filter(Boolean);
}

function marker() {
  return listMode === "todo" ? "[ ] " : "• ";
}

// Text, der wirklich gedruckt wird
function buildListText() {
  const title = $("listTitle").value.trim();
  const items = getItems();
  const lines = [];
  if (title) lines.push("[BOX]" + title);
  for (const it of items) lines.push(marker() + it);
  return lines.join("\n");
}

// Live-Vorschau des Bons
function renderBon() {
  const body = $("bonBody");
  const title = $("listTitle").value.trim();
  const items = getItems();
  let html = "";
  if (title) html += `<div class="bon-title">${escapeHtml(title)}</div>`;
  if (items.length) {
    html += '<div class="bon-items">';
    for (const it of items) {
      const mark = listMode === "todo"
        ? '<span class="bon-box"></span>'
        : '<span class="bon-dot">•</span>';
      html += `<div class="bon-item">${mark}<span>${escapeHtml(it)}</span></div>`;
    }
    html += "</div>";
  }
  if (!title && !items.length) {
    html = '<div class="bon-empty">Überschrift und Punkte eingeben…</div>';
  } else {
    html += `<div class="bon-foot">--${escapeHtml(currentUser || "Ich")}</div>`;
  }
  body.innerHTML = html;
}

async function sendList() {
  const st = $("listStatus");
  const items = getItems();
  const text = buildListText();
  if (!items.length) return setStatus(st, "Bitte mindestens einen Punkt eingeben.", "err");

  setStatus(st, "Sende…", "");
  $("sendListBtn").disabled = true;
  try {
    await createJob({ type: "text", text, username: currentUser, status: "pending" });
    setStatus(st, "Gesendet ✅", "ok");
  } catch (e) {
    setStatus(st, "Fehler: " + e.message, "err");
  } finally {
    $("sendListBtn").disabled = false;
  }
}

// ---------- Senden: Bild ----------
function previewImage() {
  const file = $("imageFile").files[0];
  imageDataUrl = "";
  imageName = "";
  $("preview").style.display = "none";
  setStatus($("imageStatus"), "", "");
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    return setStatus($("imageStatus"), "Bitte eine Bilddatei wählen.", "err");
  }
  imageName = file.name;
  downscaleImage(file, 1000, 0.85).then((dataUrl) => {
    imageDataUrl = dataUrl;
    const p = $("preview");
    p.src = dataUrl;
    p.style.display = "block";
  });
}

function downscaleImage(file, maxDim, quality) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      const scale = Math.min(1, maxDim / Math.max(width, height));
      width = Math.round(width * scale);
      height = Math.round(height * scale);
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, width, height);
      resolve(canvas.toDataURL("image/jpeg", quality));
    };
    img.src = URL.createObjectURL(file);
  });
}

async function sendImage() {
  const st = $("imageStatus");
  if (!imageDataUrl) return setStatus(st, "Bitte zuerst ein Bild wählen.", "err");

  setStatus(st, "Sende Bild…", "");
  $("sendImageBtn").disabled = true;
  try {
    await createJob({
      type: "image",
      text: "",
      image: imageDataUrl,
      filename: imageName,
      username: currentUser,
      status: "pending",
    });
    imageDataUrl = "";
    imageName = "";
    $("imageFile").value = "";
    $("preview").style.display = "none";
    setStatus(st, "Bild gesendet ✅", "ok");
  } catch (e) {
    setStatus(st, "Fehler: " + e.message, "err");
  } finally {
    $("sendImageBtn").disabled = false;
  }
}

async function createJob(job) {
  const r = await fetch(`${REST}/print_jobs`, {
    method: "POST",
    headers: HEADERS,
    body: JSON.stringify(job),
  });
  if (!r.ok) throw new Error(await r.text());
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- PWA: Installieren ----------
let deferredPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  $("installBtn").style.display = "block";
});
async function installApp() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  $("installBtn").style.display = "none";
}

// ---------- Enter-Taste zum Login ----------
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !$("loginView").hidden) login();
});

// ---------- Start ----------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("service-worker.js").catch(() => {}));
}
const saved = localStorage.getItem("druck_user");
if (saved) {
  currentUser = saved;
  openApp();
}
