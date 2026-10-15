const dropZone = document.querySelector("#drop-zone");
const picker = document.querySelector("#folder-picker");
const reviewPanel = document.querySelector("#review-panel");
const grid = document.querySelector("#thumb-grid");
const statusLine = document.querySelector("#status");
let images = [];
let draggedId = null;

function setStatus(message, kind = "") {
  statusLine.textContent = message;
  statusLine.className = `status ${kind}`;
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Something went wrong");
  return result;
}

function render() {
  grid.replaceChildren();
  images.forEach((image, index) => {
    const card = document.createElement("li");
    card.className = "thumb";
    card.draggable = true;
    card.dataset.id = image.id;
    const preview = new URL("/api/thumbnail", location.href);
    preview.searchParams.set("id", image.id);
    card.innerHTML = `
      <span class="number">${index + 1}</span>
      <img src="${preview}" alt="Preview of ${escapeHtml(image.filename)}">
      <strong title="${escapeHtml(image.filename)}">${escapeHtml(image.filename)}</strong>
      <time>${formatDate(image.capturedAt)}</time>`;
    card.addEventListener("dragstart", () => {
      draggedId = image.id;
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
    card.addEventListener("dragover", (event) => event.preventDefault());
    card.addEventListener("drop", async (event) => {
      event.preventDefault();
      if (!draggedId || draggedId === image.id) return;
      const from = images.findIndex((item) => item.id === draggedId);
      const to = images.findIndex((item) => item.id === image.id);
      images.splice(to, 0, images.splice(from, 1)[0]);
      render();
      try {
        images = (await api("/api/reorder", { ids: images.map((item) => item.id) })).images;
      } catch (error) {
        setStatus(error.message, "error");
      }
    });
    grid.append(card);
  });
  document.querySelector("#image-count").textContent = images.length;
  dropZone.hidden = true;
  reviewPanel.hidden = false;
}

function escapeHtml(value) {
  return value.replace(/[&<>"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
  })[character]);
}

function formatDate(value) {
  return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function readAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1]);
    reader.onerror = () => reject(new Error(`Could not read ${file.name}`));
    reader.readAsDataURL(file);
  });
}

async function uploadFiles(files) {
  const supported = [...files].filter((file) => {
    const path = (file.webkitRelativePath || "").split("/").filter(Boolean);
    return /\.(jpe?g|png)$/i.test(file.name) && (path.length <= 2);
  });
  if (!supported.length) throw new Error("No JPG or PNG screenshots were found");
  setStatus(`Reading ${supported.length} screenshots…`);
  const payload = await Promise.all(supported.map(async (file) => ({
    name: file.name,
    modified: file.lastModified,
    data: await readAsBase64(file),
  })));
  const result = await api("/api/upload", { files: payload });
  images = result.images;
  render();
  setStatus("Sorted by capture time. Drag any card that is out of order.");
}

async function filesFromEntry(entry) {
  if (entry.isFile) {
    return [await new Promise((resolve, reject) => entry.file(resolve, reject))];
  }
  if (!entry.isDirectory) return [];
  const reader = entry.createReader();
  const entries = [];
  while (true) {
    const batch = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
    if (!batch.length) break;
    entries.push(...batch);
  }
  return (await Promise.all(entries.filter((item) => item.isFile).map(filesFromEntry))).flat();
}

document.querySelector("#choose-folder").addEventListener("click", () => picker.click());
picker.addEventListener("change", () => uploadFiles(picker.files).catch((error) => setStatus(error.message, "error")));

for (const name of ["dragenter", "dragover"]) {
  dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
}
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", async (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  try {
    const entries = [...event.dataTransfer.items]
      .map((item) => item.webkitGetAsEntry?.())
      .filter(Boolean);
    const files = entries.length
      ? (await Promise.all(entries.map(filesFromEntry))).flat()
      : [...event.dataTransfer.files];
    await uploadFiles(files);
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.querySelector("#path-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await api("/api/import", { folder: document.querySelector("#folder-path").value });
    images = result.images;
    if (!images.length) throw new Error("No JPG or PNG screenshots were found");
    render();
    setStatus("Sorted by capture time. Drag any card that is out of order.");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.querySelector("#start-over").addEventListener("click", () => {
  images = [];
  grid.replaceChildren();
  picker.value = "";
  reviewPanel.hidden = true;
  dropZone.hidden = false;
  setStatus("");
});

document.querySelector("#export").addEventListener("click", async () => {
  const button = document.querySelector("#export");
  button.disabled = true;
  button.textContent = "Exporting…";
  try {
    const result = await api("/api/export", {
      output: document.querySelector("#output-path").value,
      perPage: Number(document.querySelector("#per-page").value),
    });
    setStatus(`Saved ${result.output}`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Export PDF";
  }
});
