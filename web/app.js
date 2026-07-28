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
let pollTimer = null;

// ---------- Hilfen ----------
function $(id) { return document.getElementById(id); }

function setStatus(el, msg, kind) {
  el.textContent = msg;
  el.className = "status" + (kind ? " " + kind : "");
}

function relTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "gerade eben";
  if (s < 3600) return `vor ${Math.floor(s / 60)} Min`;
  if (s < 86400) return `vor ${Math.floor(s / 3600)} Std`;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
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
  if (pollTimer) clearInterval(pollTimer);
  $("appView").hidden = true;
  $("loginView").hidden = false;
}

function openApp() {
  $("loginView").hidden = true;
  $("appView").hidden = false;
  $("showUser").textContent = currentUser;
  loadHistory();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(loadHistory, 3000);
}

// ---------- Tabs ----------
function showTab(which) {
  const text = which === "text";
  $("pageText").classList.toggle("active", text);
  $("pageImage").classList.toggle("active", !text);
  $("tabText").classList.toggle("active", text);
  $("tabImage").classList.toggle("active", !text);
}

// ---------- Senden: Text ----------
async function sendText() {
  const text = $("text").value.trim();
  const st = $("textStatus");
  if (!text) return setStatus(st, "Bitte Text eingeben.", "err");

  setStatus(st, "Sende…", "");
  $("sendTextBtn").disabled = true;
  try {
    await createJob({ type: "text", text, username: currentUser, status: "pending" });
    $("text").value = "";
    setStatus(st, "Gesendet ✅", "ok");
    loadHistory();
  } catch (e) {
    setStatus(st, "Fehler: " + e.message, "err");
  } finally {
    $("sendTextBtn").disabled = false;
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
    loadHistory();
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

// ---------- Verlauf ----------
async function loadHistory() {
  if (!currentUser) return;
  try {
    const q = new URLSearchParams({
      username: `eq.${currentUser}`,
      select: "id,type,text,filename,status,created_at,printed_at",
      order: "created_at.desc",
      limit: "10",
    });
    const r = await fetch(`${REST}/print_jobs?${q}`, { headers: HEADERS });
    if (!r.ok) return;
    renderJobs(await r.json());
  } catch (_) { /* offline o.ae. – still */ }
}

function renderJobs(jobs) {
  const ul = $("jobs");
  if (!jobs.length) {
    ul.innerHTML = '<li class="empty">Noch nichts gedruckt.</li>';
    return;
  }
  const label = { pending: "wartet", printed: "gedruckt", error: "Fehler" };
  ul.innerHTML = jobs
    .map((j) => {
      const isImg = j.type === "image" || !!j.filename;
      const ic = isImg ? "🖼️" : "📝";
      let title = isImg ? (j.filename || "Bild") : (j.text || "").replace(/\s+/g, " ").trim();
      if (title.length > 42) title = title.slice(0, 42) + "…";
      if (!title) title = isImg ? "Bild" : "(leer)";
      const status = j.status || "pending";
      const when = status === "printed" ? relTime(j.printed_at) : relTime(j.created_at);
      return `<li class="job">
        <div class="ic">${ic}</div>
        <div class="body">
          <div class="t">${escapeHtml(title)}</div>
          <div class="time">${when}</div>
        </div>
        <span class="badge ${status}">${label[status] || status}</span>
      </li>`;
    })
    .join("");
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
