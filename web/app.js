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

const EXPIRY_MS = 2 * 60 * 1000;
let currentFile = null;
let expiryTimeout = null;
let expiryInterval = null;

function setHealth(state, label) {
  healthDot.className = "dot " + state;
  healthLabel.textContent = label;
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    setHealth("ok", data.engine + " · ready");
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

function setFile(file) {
  if (!file) return;
  currentFile = file;
  previewName.textContent = file.name + "  ·  " + (file.size / 1024).toFixed(0) + " KB";
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    dzEmpty.hidden = true;
    dzPreview.hidden = false;
    runBtn.disabled = false;
    clearError();
  };
  reader.readAsDataURL(file);
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
  dzPreview.hidden = true;
  dzPreview.querySelector("img").removeAttribute("src");
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
    const res = await fetch("/api/ocr", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Server error (" + res.status + ").");

    resultText.value = data.text || "";
    resultPanel.hidden = false;
    resultMeta.textContent = data.note
      ? data.note + " · " + data.duration_ms + " ms"
      : data.confidence.toFixed(1) + "% conf · " + data.duration_ms + " ms";
    copyBtn.disabled = resultText.value.trim().length === 0;
    downloadBtn.disabled = resultText.value.trim().length === 0;
    if (data.text && data.text.trim()) startExpiry();
  } catch (err) {
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