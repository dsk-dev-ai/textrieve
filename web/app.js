const $ = (sel) => document.querySelector(sel);

const dropzone = $("#dropzone");
const fileInput = $("#file-input");
const dzEmpty = $("#dz-empty");
const dzPreview = $("#dz-preview");
const previewImg = $("#preview-img");
const previewName = $("#preview-name");
const clearBtn = $("#clear-btn");
const runBtn = $("#run-btn");
const resultPanel = $("#result-panel");
const resultText = $("#result-text");
const resultMeta = $("#result-meta");
const copyBtn = $("#copy-btn");
const downloadBtn = $("#download-btn");
const errorBox = $("#error");
const expiresEl = $("#expires");
const healthDot = $("#health-dot");
const healthLabel = $("#health-label");
const progressBox = $("#progress");
const progressFill = $("#progress-fill");
const progressPct = $("#progress-pct");
const progressSec = $("#progress-sec");

const EXPIRY_MS = 2 * 60 * 1000;
let currentFile = null;
let expiryTimeout = null;
let expiryInterval = null;
let apiBase = "";

// The UI is served from the same Render instance as the OCR API. Prefer the
// same origin; the public fallback keeps a standalone copy of web/ working too.
const FALLBACK_API = "https://textrieve.onrender.com";

async function resolveApiBase() {
  if (apiBase) return apiBase;
  for (const base of ["", FALLBACK_API]) {
    try {
      const res = await fetch((base || "/") + "api/health", {
        signal: AbortSignal.timeout(6000),
      });
      if (res.ok) {
        apiBase = base;
        return base;
      }
    } catch {
      /* try next candidate */
    }
  }
  return "";
}

async function call(path, options) {
  const base = await resolveApiBase();
  const res = await fetch(base + path, options);
  return res;
}

function apiUrl(path) {
  return (apiBase || "") + path;
}

function setHealth(state, label) {
  healthDot.className = "dot " + state;
  healthLabel.textContent = label;
}

async function checkHealth() {
  try {
    const res = await call("api/health");
    if (!res.ok) throw new Error("health " + res.status);
    const data = await res.json();
    setHealth("ok", (apiBase ? "remote · " : "") + data.engine + " · ready");
  } catch {
    setHealth("bad", "engine unavailable");
  }
}

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.hidden = false;
}
function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

// Progress is driven by real elapsed wall-clock time (the "speed" you actually
// experience), not a fake timer. An adaptive expected-duration curve keeps it
// climbing at a believable pace no matter how slow the free tier is.
let progressTimer = null;

function startProgress(note) {
  clearInterval(progressTimer);
  const t0 = performance.now();
  let expected = 9000; // ms we optimistically expect OCR to need
  progressBox.hidden = false;
  progressFill.style.width = "0%";
  progressPct.textContent = "0%";
  progressSec.textContent = note || "0.0s";
  progressTimer = setInterval(() => {
    const elapsed = performance.now() - t0;
    expected = Math.max(expected, elapsed * 1.5 + 2500); // adapt to real speed
    const pct = Math.min(95, 100 * (1 - Math.exp(-elapsed / expected)));
    progressFill.style.width = pct.toFixed(1) + "%";
    progressPct.textContent = Math.round(pct) + "%";
    progressSec.textContent = (elapsed / 1000).toFixed(1) + "s";
  }, 200);
}

function finishProgress() {
  clearInterval(progressTimer);
  progressTimer = null;
  progressFill.style.width = "100%";
  progressPct.textContent = "100%";
  setTimeout(() => {
    progressBox.hidden = true;
    progressFill.style.width = "0%";
  }, 450);
}

function setFile(file) {
  if (!file) return;
  currentFile = file;
  previewName.textContent = file.name + "  ·  " + (file.size / 1024).toFixed(0) + " KB";
  const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
  if (isPdf) {
    // Browsers can't paint a PDF into an <img>; show a file chip instead.
    previewImg.hidden = true;
    previewName.textContent = "PDF  ·  " + file.name + "  ·  " + (file.size / 1024).toFixed(0) + " KB";
  } else {
    previewImg.hidden = false;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }
  dzEmpty.hidden = true;
  dzPreview.hidden = false;
  runBtn.disabled = false;
  clearError();
}

function clearExpiry() {
  clearTimeout(expiryTimeout);
  clearInterval(expiryInterval);
  expiryTimeout = null;
  expiryInterval = null;
  expiresEl.hidden = true;
  expiresEl.textContent = "";
}

function startExpiry() {
  clearExpiry();
  const deadline = Date.now() + EXPIRY_MS;
  expiresEl.hidden = false;
  const tick = () => {
    const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
    const m = Math.floor(left / 60);
    const s = String(left % 60).padStart(2, "0");
    expiresEl.textContent = "auto-clears in " + m + ":" + s;
  };
  tick();
  expiryInterval = setInterval(tick, 1000);
  expiryTimeout = setTimeout(() => {
    clearExpiry();
    resultText.value = "";
    resultPanel.hidden = true;
    copyBtn.disabled = true;
    downloadBtn.disabled = true;
  }, EXPIRY_MS);
}

function reset() {
  currentFile = null;
  fileInput.value = "";
  clearInterval(progressTimer);
  progressTimer = null;
  progressBox.hidden = true;
  progressFill.style.width = "0%";
  dzPreview.hidden = true;
  previewImg.hidden = false;
  previewImg.removeAttribute("src");
  dzEmpty.hidden = false;
  runBtn.disabled = true;
  resultPanel.hidden = true;
  clearExpiry();
  clearError();
}

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
clearBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  reset();
});

["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("drag");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files && e.dataTransfer.files[0];
  if (file) setFile(file);
});

runBtn.addEventListener("click", async () => {
  if (!currentFile) return;
  runBtn.disabled = true;
  runBtn.textContent = "Extracting…";
  clearError();
  try {
    const fd = new FormData();
    fd.append("file", currentFile);
    startProgress();

    let res, data;
    // Render's free instances spin down when idle (~15 min). The first OCR
    // after that can be slow or bounce an HTML proxy page while it wakes up,
    // so retry once before giving up.
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        res = await call("api/ocr", { method: "POST", body: fd });
      } catch (netErr) {
        if (attempt === 1) {
          startProgress("engine waking up — retrying…");
          await new Promise((r) => setTimeout(r, 12000));
          continue;
        }
        throw netErr;
      }
      data = null;
      try {
        data = await res.json();
      } catch {
        data = null;
      }
      const wakeup = !res.ok && (!data || res.status >= 500);
      if (wakeup && attempt === 1) {
        startProgress("engine waking up — retrying…");
        await new Promise((r) => setTimeout(r, 12000));
        continue;
      }
      break;
    }

    if (!res.ok || !data) {
      const reason = !data
        ? "The OCR engine is not responding (free instance waking up). Wait ~30 s and try again."
        : data.detail || "Server error (" + res.status + ").";
      throw new Error(reason);
    }

    finishProgress();
    resultText.value = data.text || "";
    resultPanel.hidden = false;
    const pagePrefix = data.pages && data.pages > 1 ? data.pages + " pages · " : "";
    resultMeta.textContent = data.note
      ? data.note + " · " + data.duration_ms + " ms"
      : pagePrefix + data.confidence.toFixed(1) + "% conf · " + data.duration_ms + " ms";
    copyBtn.disabled = resultText.value.trim().length === 0;
    downloadBtn.disabled = resultText.value.trim().length === 0;
    if (data.text && data.text.trim()) startExpiry();
  } catch (err) {
    clearInterval(progressTimer);
    progressTimer = null;
    progressBox.hidden = true;
    showError(err.message);
  } finally {
    runBtn.disabled = !currentFile;
    runBtn.textContent = "Extract text";
  }
});

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(resultText.value);
    copyBtn.textContent = "Copied";
    setTimeout(() => (copyBtn.textContent = "Copy"), 1400);
  } catch {
    resultText.select();
    document.execCommand("copy");
  }
});

downloadBtn.addEventListener("click", () => {
  const base = (currentFile ? currentFile.name.replace(/\.[^.]+$/, "") : "text") + ".txt";
  const blob = new Blob([resultText.value], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = base;
  a.click();
  URL.revokeObjectURL(a.href);
});

checkHealth();