import { icon, mountIcons } from "./icons.js";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const elements = {
  accountSelect: $("#accountSelect"),
  dataRootButton: $("#dataRootButton"),
  demoButton: $("#demoButton"),
  scanButton: $("#scanButton"),
  emptyScanButton: $("#emptyScanButton"),
  emptyDemoButton: $("#emptyDemoButton"),
  refreshButton: $("#refreshButton"),
  themeButton: $("#themeButton"),
  globalStatus: $("#globalStatus"),
  sidebar: $("#sidebar"),
  sidebarToggle: $("#sidebarToggle"),
  inspector: $("#inspector"),
  inspectorClose: $("#inspectorClose"),
  groupFilters: $("#groupFilters"),
  typeFilters: $("#typeFilters"),
  seedInput: $("#seedInput"),
  keyInput: $("#keyInput"),
  nameFromDbInput: $("#nameFromDbInput"),
  clearLibraryButton: $("#clearLibraryButton"),
  summaryTotal: $("#summaryTotal"),
  summaryAnimated: $("#summaryAnimated"),
  summarySize: $("#summarySize"),
  summaryGroups: $("#summaryGroups"),
  searchInput: $("#searchInput"),
  sortSelect: $("#sortSelect"),
  viewControls: $("#viewControls"),
  resultSummary: $("#resultSummary"),
  selectedSummary: $("#selectedSummary"),
  selectVisibleButton: $("#selectVisibleButton"),
  clearSelectionButton: $("#clearSelectionButton"),
  saveButton: $("#saveButton"),
  emptyState: $("#emptyState"),
  emptyMessage: $("#emptyMessage"),
  itemsGrid: $("#itemsGrid"),
  loadMoreButton: $("#loadMoreButton"),
  inspectorEmpty: $("#inspectorEmpty"),
  inspectorContent: $("#inspectorContent"),
  previewImage: $("#previewImage"),
  previewPlaceholder: $("#previewPlaceholder"),
  previewBadge: $("#previewBadge"),
  itemTitle: $("#itemTitle"),
  itemSubtitle: $("#itemSubtitle"),
  favoriteButton: $("#favoriteButton"),
  previewSpeed: $("#previewSpeed"),
  previewSpeedNumber: $("#previewSpeedNumber"),
  previewSpeedPresets: $("#previewSpeedPresets"),
  itemDetails: $("#itemDetails"),
  saveItemButton: $("#saveItemButton"),
  selectItemButton: $("#selectItemButton"),
  jobPanel: $("#jobPanel"),
  jobTitle: $("#jobTitle"),
  jobPercent: $("#jobPercent"),
  jobMessage: $("#jobMessage"),
  jobBar: $("#jobBar"),
  jobCloseButton: $("#jobCloseButton"),
  dataRootDialog: $("#dataRootDialog"),
  dataRootInput: $("#dataRootInput"),
  detectedRootsList: $("#detectedRootsList"),
  applyDataRootButton: $("#applyDataRootButton"),
  exportDialog: $("#exportDialog"),
  exportSelectionCount: $("#exportSelectionCount"),
  exportSpeedControls: $("#exportSpeedControls"),
  exportSpeedRange: $("#exportSpeedRange"),
  exportSpeedNumber: $("#exportSpeedNumber"),
  exportPath: $("#exportPath"),
  preserveGroupsInput: $("#preserveGroupsInput"),
  exportStatus: $("#exportStatus"),
  exportProgressBar: $("#exportProgressBar"),
  exportStatusText: $("#exportStatusText"),
  zipButton: $("#zipButton"),
  browserFolderButton: $("#browserFolderButton"),
  saveFolderButton: $("#saveFolderButton"),
  toastStack: $("#toastStack"),
};

const state = {
  health: null,
  accounts: [],
  roots: [],
  manualRoots: readStorageJSON("studio.manualRoots", []),
  library: null,
  filtered: [],
  selected: new Set(),
  favorites: new Set(readStorageJSON("studio.favorites", [])),
  activeId: null,
  groupFilter: "all",
  typeFilter: "all",
  query: "",
  sort: "name",
  view: readStorageJSON("studio.view", "grid"),
  previewSpeed: 1,
  exportSpeed: 1,
  exportIds: [],
  renderLimit: 240,
  jobTimer: null,
};

const GROUP_LABELS = {
  Persist: "原图",
  PersistStore: "表情包原图",
  Thumb: "缩略图",
  ThumbStore: "表情包缩略图",
  Temp: "临时文件",
};

function groupLabel(group) {
  return GROUP_LABELS[group] || group;
}

function clampSpeed(value) {
  const speed = Number(value);
  if (!Number.isFinite(speed)) return 1;
  return Math.min(4, Math.max(0.1, speed));
}

function formatSpeed(value) {
  const speed = clampSpeed(value);
  return Number.isInteger(speed) ? speed.toFixed(1) : String(Number(speed.toFixed(2)));
}

function readStorageJSON(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : JSON.parse(value);
  } catch {
    return fallback;
  }
}

function writeStorageJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage can be unavailable in hardened browser profiles.
  }
}

async function api(path, options = {}) {
  const init = { ...options, headers: { ...(options.headers || {}) } };
  if (init.body && typeof init.body !== "string") {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(init.body);
  }
  const response = await fetch(path, init);
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    throw new Error(payload?.error || `请求失败 (${response.status})`);
  }
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`;
}

function formatDuration(ms) {
  if (!ms) return "-";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
}

function contentUrl(item, speed = 1, download = false) {
  const params = new URLSearchParams({ speed: String(speed) });
  if (download) params.set("download", "1");
  return `/api/libraries/${encodeURIComponent(state.library.id)}/items/${encodeURIComponent(item.id)}/content?${params}`;
}

function safeDownloadName(name, used) {
  let cleaned = String(name || "emoticon")
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_")
    .replace(/^[.\s]+|[.\s]+$/g, "");
  if (!cleaned) cleaned = "emoticon";
  const dot = cleaned.lastIndexOf(".");
  const stem = dot > 0 ? cleaned.slice(0, dot) : cleaned;
  const suffix = dot > 0 ? cleaned.slice(dot) : "";
  let candidate = cleaned;
  let index = 2;
  while (used.has(candidate.toLocaleLowerCase())) {
    candidate = `${stem}_${index}${suffix}`;
    index += 1;
  }
  used.add(candidate.toLocaleLowerCase());
  return candidate;
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const next = theme === "dark" ? "sun" : "moon";
  elements.themeButton.innerHTML = icon(next);
  writeStorageJSON("studio.theme", theme);
}

function initTheme() {
  const saved = readStorageJSON("studio.theme", null);
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  setTheme(saved || (prefersDark ? "dark" : "light"));
}

function toast(message, type = "success") {
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  node.innerHTML = `${icon(type === "error" ? "info" : "check")}<span>${escapeHtml(message)}</span>`;
  elements.toastStack.append(node);
  window.setTimeout(() => node.remove(), 4200);
}

async function loadHealth() {
  try {
    state.health = await api("/api/health");
    elements.globalStatus.textContent = state.health.ffmpeg_available ? "动图转码可用" : "未检测到 ffmpeg";
  } catch (error) {
    elements.globalStatus.textContent = "后端连接失败";
    toast(error.message, "error");
  }
}

function accountQuery() {
  const params = new URLSearchParams();
  state.manualRoots.forEach((root) => {
    if (root) params.append("data_root", root);
  });
  const suffix = params.toString();
  return suffix ? `?${suffix}` : "";
}

async function loadAccounts() {
  elements.refreshButton.disabled = true;
  try {
    const data = await api(`/api/accounts${accountQuery()}`);
    state.accounts = data.accounts || [];
    state.roots = data.roots || [];
    const previous = elements.accountSelect.value;
    elements.accountSelect.innerHTML = "";
    if (!state.accounts.length) {
      elements.accountSelect.innerHTML = '<option value="">未检测到账号</option>';
    } else {
      state.accounts.forEach((account, index) => {
        const option = document.createElement("option");
        option.value = account.folder_name;
        const activeHint = index === 0 && state.accounts.length > 1 ? " · 最近使用" : "";
        const displayName = account.display_name || account.folder_name;
        option.textContent = `${displayName}${activeHint}${account.has_emoticon ? "" : " · 无表情目录"}`;
        option.title = account.display_name ? account.folder_name : "";
        option.disabled = !account.has_emoticon;
        elements.accountSelect.append(option);
      });
      const previousOption = [...elements.accountSelect.options].find((option) => option.value === previous && !option.disabled);
      const firstEnabled = [...elements.accountSelect.options].find((option) => !option.disabled);
      elements.accountSelect.value = previousOption?.value || firstEnabled?.value || "";
    }
    const available = Boolean(elements.accountSelect.value);
    elements.scanButton.disabled = !available;
    elements.emptyScanButton.disabled = !available;
    if (!state.library) {
      elements.emptyMessage.textContent = available
        ? "账号已就绪，可以读取本机自定义表情。"
        : "未检测到微信账号，可配置数据目录或打开演示。";
    }
    renderRoots();
    if (available && !state.library && new URLSearchParams(location.search).get("demo") !== "1") {
      elements.globalStatus.textContent = "账号已就绪";
    }
  } catch (error) {
    toast(error.message, "error");
  } finally {
    elements.refreshButton.disabled = false;
  }
}

function renderRoots() {
  elements.detectedRootsList.innerHTML = "";
  if (!state.roots.length) {
    elements.detectedRootsList.innerHTML = '<span class="root-option">未发现自动路径</span>';
    return;
  }
  state.roots.forEach((root) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "root-option";
    button.textContent = root;
    button.title = root;
    button.addEventListener("click", () => {
      elements.dataRootInput.value = root;
    });
    elements.detectedRootsList.append(button);
  });
}

function setJob(progress, message, title = "正在读取表情") {
  elements.jobPanel.hidden = false;
  elements.jobTitle.textContent = title;
  elements.jobPercent.textContent = `${Math.round(progress)}%`;
  elements.jobMessage.textContent = message || "处理中";
  elements.jobBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
}

async function scanLibrary() {
  const account = elements.accountSelect.value;
  if (!account) {
    toast("请先选择微信账号", "error");
    return;
  }
  const seedText = elements.seedInput.value.trim();
  const payload = {
    account,
    data_roots: state.manualRoots,
    seed: seedText ? Number(seedText) : null,
    key: elements.keyInput.value.trim() || null,
    name_from_db: elements.nameFromDbInput.checked,
  };
  if (seedText && !Number.isFinite(payload.seed)) {
    toast("Seed 必须是数字", "error");
    return;
  }
  elements.scanButton.disabled = true;
  elements.emptyScanButton.disabled = true;
  clearInterval(state.jobTimer);
  setJob(2, "正在创建扫描任务");
  try {
    const data = await api("/api/scan", { method: "POST", body: payload });
    await pollJob(data.job.id);
  } catch (error) {
    setJob(100, error.message, "读取失败");
    toast(error.message, "error");
  } finally {
    elements.scanButton.disabled = !elements.accountSelect.value;
    elements.emptyScanButton.disabled = !elements.accountSelect.value;
  }
}

async function pollJob(jobId) {
  while (true) {
    const data = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
    const job = data.job;
    setJob(job.progress, job.message);
    if (job.status === "complete") {
      activateLibrary(job.result.library);
      setJob(100, job.message, "读取完成");
      window.setTimeout(() => {
        elements.jobPanel.hidden = true;
      }, 1800);
      return;
    }
    if (job.status === "failed") {
      throw new Error(job.error || "扫描失败");
    }
    await new Promise((resolve) => window.setTimeout(resolve, 420));
  }
}

async function loadDemo() {
  clearInterval(state.jobTimer);
  setJob(16, "正在准备演示素材", "加载演示");
  try {
    const data = await api("/api/demo", { method: "POST" });
    setJob(100, "演示素材已就绪", "加载完成");
    activateLibrary(data.library);
    window.setTimeout(() => {
      elements.jobPanel.hidden = true;
    }, 1100);
  } catch (error) {
    setJob(100, error.message, "加载失败");
    toast(error.message, "error");
  }
}

function activateLibrary(library) {
  state.library = library;
  state.selected.clear();
  state.activeId = null;
  state.groupFilter = "all";
  state.typeFilter = "all";
  state.query = "";
  state.renderLimit = 240;
  elements.searchInput.value = "";
  elements.globalStatus.textContent = `${library.account} · ${library.total} 个表情`;
  elements.clearLibraryButton.disabled = false;
  elements.emptyState.hidden = true;
  renderSummary();
  renderGroupFilters();
  renderTypeFilters();
  applyFilters();
  renderInspector();
  closeMobilePanels();
}

function renderSummary() {
  if (!state.library) return;
  elements.summaryTotal.textContent = state.library.total;
  elements.summaryAnimated.textContent = state.library.animated;
  elements.summarySize.textContent = formatBytes(state.library.total_size);
  elements.summaryGroups.textContent = Object.keys(state.library.groups || {}).length;
}

function renderGroupFilters() {
  const groups = state.library?.groups || {};
  const entries = Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  const buttons = [
    `<button class="chip ${state.groupFilter === "all" ? "active" : ""}" data-group="all">全部 <em>${state.library?.total || 0}</em></button>`,
    ...entries.map(
      ([group, count]) =>
        `<button class="chip ${state.groupFilter === group ? "active" : ""}" data-group="${escapeHtml(group)}" title="${escapeHtml(group)}">${escapeHtml(groupLabel(group))} <em>${count}</em></button>`,
    ),
  ];
  elements.groupFilters.innerHTML = buttons.join("");
}

function renderTypeFilters() {
  $$("#typeFilters button").forEach((button) => {
    button.classList.toggle("active", button.dataset.type === state.typeFilter);
  });
}

function applyFilters() {
  if (!state.library) {
    state.filtered = [];
    renderItems();
    return;
  }
  const query = state.query.trim().toLocaleLowerCase();
  let items = state.library.items.filter((item) => {
    if (state.groupFilter !== "all" && item.group !== state.groupFilter) return false;
    if (state.typeFilter === "animated" && !item.animated) return false;
    if (state.typeFilter === "static" && (item.animated || !item.previewable)) return false;
    if (state.typeFilter === "thumbnail" && item.category !== "thumbnail") return false;
    if (query && !`${item.name} ${item.group} ${item.relative_path}`.toLocaleLowerCase().includes(query)) return false;
    return true;
  });
  items.sort((a, b) => {
    if (state.sort === "size") return b.size - a.size;
    if (state.sort === "modified") return b.modified_at - a.modified_at;
    if (state.sort === "frames") return (b.frame_count || 0) - (a.frame_count || 0);
    return a.name.localeCompare(b.name, "zh-CN", { numeric: true });
  });
  state.filtered = items;
  state.renderLimit = 240;
  renderItems();
}

function renderItems() {
  if (!state.library) {
    elements.itemsGrid.innerHTML = "";
    elements.loadMoreButton.hidden = true;
    elements.emptyState.hidden = false;
    updateSelectionUI();
    return;
  }
  elements.emptyState.hidden = true;
  const visible = state.filtered.slice(0, state.renderLimit);
  elements.itemsGrid.classList.toggle("list-view", state.view === "list");
  elements.itemsGrid.innerHTML = visible.map(renderCard).join("");
  elements.loadMoreButton.hidden = visible.length >= state.filtered.length;
  elements.resultSummary.textContent = `${state.filtered.length} 个结果`;
  updateSelectionUI();
}

function renderCard(item) {
  const selected = state.selected.has(item.id);
  const favorite = state.favorites.has(item.id);
  const preview = item.previewable
    ? `<img src="${contentUrl(item, 1)}" loading="lazy" decoding="async" alt="">`
    : `<span class="card-placeholder">${icon("image")}</span>`;
  const badge = item.animated ? "动图" : "静态";
  const dimensions = item.width && item.height ? `${item.width}×${item.height}` : "-";
  return `
    <article class="emoticon-card ${selected ? "selected" : ""} ${state.activeId === item.id ? "active" : ""}" data-item-id="${item.id}">
      <div class="card-preview" data-action="open" role="button" tabindex="0" aria-label="预览 ${escapeHtml(item.name)}">
        ${preview}
        <span class="card-badge">${escapeHtml(badge)}</span>
        <button class="selection-toggle ${selected ? "checked" : ""}" data-action="toggle" aria-label="${selected ? "取消选择" : "选择"}" aria-pressed="${selected}">
          ${icon("check")}
        </button>
      </div>
      <div class="card-body">
        <div class="card-copy">
          <span class="card-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
          <span class="card-meta">${escapeHtml(groupLabel(item.group))} · ${dimensions}</span>
        </div>
        <button class="icon-button card-favorite ${favorite ? "active" : ""}" data-action="favorite" title="收藏" aria-label="收藏">
          ${icon("heart")}
        </button>
      </div>
    </article>`;
}

function selectItem(itemId, openInspector = true) {
  state.activeId = itemId;
  if (openInspector) elements.inspector.classList.add("open");
  renderItems();
  renderInspector();
}

function toggleSelected(itemId) {
  if (state.selected.has(itemId)) state.selected.delete(itemId);
  else state.selected.add(itemId);
  renderItems();
  renderInspector();
}

function updateSelectionUI() {
  const count = state.selected.size;
  elements.selectedSummary.textContent = count ? `已选择 ${count} 个` : "未选择";
  elements.saveButton.disabled = count === 0;
  elements.clearSelectionButton.disabled = count === 0;
  elements.selectVisibleButton.disabled = state.filtered.length === 0;
  if (state.activeId) {
    const selected = state.selected.has(state.activeId);
    elements.selectItemButton.innerHTML = `${icon(selected ? "x" : "check")}${selected ? "移出选择" : "加入选择"}`;
  }
}

function renderInspector() {
  const item = activeItem();
  if (!item) {
    elements.inspectorEmpty.hidden = false;
    elements.inspectorContent.hidden = true;
    return;
  }
  elements.inspectorEmpty.hidden = true;
  elements.inspectorContent.hidden = false;
  elements.itemTitle.textContent = item.name;
  elements.itemSubtitle.textContent = `${groupLabel(item.group)} · ${item.relative_path}`;
  elements.previewBadge.textContent = item.animated ? "GIF 动图" : item.extension.slice(1).toUpperCase();
  elements.favoriteButton.classList.toggle("active", state.favorites.has(item.id));
  elements.previewSpeed.closest(".speed-panel").hidden = !item.animated;
  elements.previewSpeed.value = String(state.previewSpeed);
  elements.previewSpeedNumber.value = formatSpeed(state.previewSpeed);
  $$("#previewSpeedPresets button").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.speed) === state.previewSpeed);
  });

  if (item.previewable) {
    elements.previewImage.hidden = false;
    elements.previewPlaceholder.hidden = true;
    elements.previewImage.src = contentUrl(item, state.previewSpeed);
    elements.previewImage.alt = item.name;
  } else {
    elements.previewImage.hidden = true;
    elements.previewImage.removeAttribute("src");
    elements.previewPlaceholder.hidden = false;
  }

  const details = [
    ["格式", item.extension.slice(1).toUpperCase()],
    ["尺寸", item.width && item.height ? `${item.width} × ${item.height}` : "-"],
    ["文件大小", formatBytes(item.size)],
    ["帧数", item.frame_count],
    ["时长", formatDuration(item.duration_ms)],
    ["来源", groupLabel(item.group)],
  ];
  elements.itemDetails.innerHTML = details
    .map(([label, value]) => `<div><dt>${label}</dt><dd title="${escapeHtml(value)}">${escapeHtml(value)}</dd></div>`)
    .join("");
  updateSelectionUI();
}

function activeItem() {
  if (!state.library || !state.activeId) return null;
  return state.library.items.find((item) => item.id === state.activeId) || null;
}

function setPreviewSpeed(speed) {
  state.previewSpeed = clampSpeed(speed);
  elements.previewSpeed.value = String(state.previewSpeed);
  elements.previewSpeedNumber.value = formatSpeed(state.previewSpeed);
  renderInspector();
}

function setExportSpeed(speed) {
  state.exportSpeed = clampSpeed(speed);
  updateExportSpeedButtons();
}

function toggleFavorite(itemId) {
  if (state.favorites.has(itemId)) state.favorites.delete(itemId);
  else state.favorites.add(itemId);
  writeStorageJSON("studio.favorites", [...state.favorites]);
  renderItems();
  renderInspector();
}

function openExportDialog(itemIds = [...state.selected]) {
  if (!state.library || !itemIds.length) {
    toast("请先选择要保存的表情", "error");
    return;
  }
  state.exportIds = [...new Set(itemIds)];
  state.exportSpeed = clampSpeed(state.previewSpeed);
  elements.exportSelectionCount.textContent = state.exportIds.length;
  elements.exportPath.value = readStorageJSON("studio.exportPath", "");
  elements.preserveGroupsInput.checked = readStorageJSON("studio.preserveGroups", true);
  elements.exportStatus.hidden = true;
  elements.exportProgressBar.style.width = "0%";
  updateExportSpeedButtons();
  elements.browserFolderButton.hidden = !("showDirectoryPicker" in window);
  elements.exportDialog.showModal();
}

function updateExportSpeedButtons() {
  elements.exportSpeedRange.value = String(state.exportSpeed);
  elements.exportSpeedNumber.value = formatSpeed(state.exportSpeed);
  $$("#exportSpeedControls button").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.speed) === state.exportSpeed);
  });
}

function setExportProgress(progress, text) {
  elements.exportStatus.hidden = false;
  elements.exportProgressBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  elements.exportStatusText.textContent = text;
}

function suggestedSaveName(item, speed) {
  const dot = item.name.lastIndexOf(".");
  const stem = dot > 0 ? item.name.slice(0, dot) : item.name;
  const suffix = dot > 0 ? item.name.slice(dot) : item.extension;
  const speedTag = Math.abs(speed - 1) < 0.001 ? "" : `_${formatSpeed(speed)}x`;
  return `${stem}${speedTag}${suffix}`;
}

async function saveCurrentConfig() {
  const item = activeItem();
  if (!item) return;
  const suggestedName = suggestedSaveName(item, state.previewSpeed);

  try {
    if (window.pywebview?.api?.choose_save_path) {
      const targetFile = await window.pywebview.api.choose_save_path(suggestedName);
      if (!targetFile) return;
      const result = await api(
        `/api/libraries/${encodeURIComponent(state.library.id)}/items/${encodeURIComponent(item.id)}/save`,
        {
          method: "POST",
          body: { target_file: targetFile, speed: state.previewSpeed },
        },
      );
      toast(`已保存到 ${result.saved}`);
      return;
    }

    if ("showSaveFilePicker" in window) {
      const handle = await window.showSaveFilePicker({
        suggestedName,
        types: [
          {
            description: "GIF 动图",
            accept: { "image/gif": [".gif"] },
          },
        ],
      });
      const response = await fetch(contentUrl(item, state.previewSpeed, true));
      if (!response.ok) throw new Error("无法读取当前表情");
      const writable = await handle.createWritable();
      await writable.write(await response.blob());
      await writable.close();
      toast(`已保存 ${suggestedName}`);
      return;
    }
  } catch (error) {
    if (error.name !== "AbortError") toast(error.message, "error");
    return;
  }

  openExportDialog([item.id]);
}

async function saveToFolderPath() {
  const targetDir = elements.exportPath.value.trim();
  if (!targetDir) {
    toast("请输入保存文件夹路径", "error");
    return;
  }
  writeStorageJSON("studio.exportPath", targetDir);
  writeStorageJSON("studio.preserveGroups", elements.preserveGroupsInput.checked);
  elements.saveFolderButton.disabled = true;
  setExportProgress(12, "正在准备文件");
  try {
    const data = await api(`/api/libraries/${encodeURIComponent(state.library.id)}/export`, {
      method: "POST",
      body: {
        item_ids: state.exportIds,
        target_dir: targetDir,
        speed: state.exportSpeed,
        preserve_groups: elements.preserveGroupsInput.checked,
      },
    });
    setExportProgress(100, `已保存 ${data.count} 个文件到 ${data.target_dir}`);
    toast(`已保存 ${data.count} 个表情`);
  } catch (error) {
    setExportProgress(100, error.message);
    toast(error.message, "error");
  } finally {
    elements.saveFolderButton.disabled = false;
  }
}

async function saveToBrowserFolder() {
  if (!("showDirectoryPicker" in window)) return;
  let directory;
  try {
    directory = await window.showDirectoryPicker({ mode: "readwrite" });
  } catch (error) {
    if (error.name !== "AbortError") toast(error.message, "error");
    return;
  }
  elements.browserFolderButton.disabled = true;
  const itemMap = new Map(state.library.items.map((item) => [item.id, item]));
  const used = new Set();
  let completed = 0;
  try {
    for (const itemId of state.exportIds) {
      const item = itemMap.get(itemId);
      if (!item) continue;
      setExportProgress((completed / state.exportIds.length) * 100, `正在保存 ${item.name}`);
      const response = await fetch(contentUrl(item, state.exportSpeed, true));
      if (!response.ok) throw new Error(`无法读取 ${item.name}`);
      const blob = await response.blob();
      const filename = safeDownloadName(item.name, used);
      const handle = await directory.getFileHandle(filename, { create: true });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      completed += 1;
    }
    setExportProgress(100, `已保存 ${completed} 个文件到 ${directory.name}`);
    toast(`已保存 ${completed} 个表情`);
  } catch (error) {
    setExportProgress(100, error.message);
    toast(error.message, "error");
  } finally {
    elements.browserFolderButton.disabled = false;
  }
}

async function downloadZip() {
  elements.zipButton.disabled = true;
  setExportProgress(18, "正在打包 ZIP");
  try {
    const response = await fetch(`/api/libraries/${encodeURIComponent(state.library.id)}/archive`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_ids: state.exportIds, speed: state.exportSpeed }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || "打包失败");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `wechat-emoticons-${Date.now()}.zip`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setExportProgress(100, `ZIP 已生成，共 ${state.exportIds.length} 个文件`);
  } catch (error) {
    setExportProgress(100, error.message);
    toast(error.message, "error");
  } finally {
    elements.zipButton.disabled = false;
  }
}

async function clearLibrary() {
  if (!state.library) return;
  const libraryId = state.library.id;
  state.library = null;
  state.selected.clear();
  state.activeId = null;
  elements.clearLibraryButton.disabled = true;
  elements.globalStatus.textContent = "缓存已清理";
  elements.emptyState.hidden = false;
  elements.emptyMessage.textContent = "选择微信账号后读取本机自定义表情。";
  renderSummaryEmpty();
  renderItems();
  renderInspector();
  try {
    await api(`/api/libraries/${encodeURIComponent(libraryId)}`, { method: "DELETE" });
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderSummaryEmpty() {
  elements.summaryTotal.textContent = "0";
  elements.summaryAnimated.textContent = "0";
  elements.summarySize.textContent = "0 B";
  elements.summaryGroups.textContent = "0";
  elements.groupFilters.innerHTML = "";
  state.filtered = [];
  elements.resultSummary.textContent = "0 个结果";
  updateSelectionUI();
}

function closeMobilePanels() {
  elements.sidebar.classList.remove("open");
  elements.inspector.classList.remove("open");
}

function bindEvents() {
  elements.scanButton.addEventListener("click", scanLibrary);
  elements.emptyScanButton.addEventListener("click", scanLibrary);
  elements.demoButton.addEventListener("click", loadDemo);
  elements.emptyDemoButton.addEventListener("click", loadDemo);
  elements.refreshButton.addEventListener("click", loadAccounts);
  elements.themeButton.addEventListener("click", () => {
    setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  });
  elements.sidebarToggle.addEventListener("click", () => elements.sidebar.classList.toggle("open"));
  elements.inspectorClose.addEventListener("click", () => elements.inspector.classList.remove("open"));
  elements.jobCloseButton.addEventListener("click", () => {
    elements.jobPanel.hidden = true;
  });

  elements.dataRootButton.addEventListener("click", () => {
    elements.dataRootInput.value = state.manualRoots[0] || "";
    renderRoots();
    elements.dataRootDialog.showModal();
  });
  elements.applyDataRootButton.addEventListener("click", (event) => {
    event.preventDefault();
    const root = elements.dataRootInput.value.trim();
    state.manualRoots = root ? [root] : [];
    writeStorageJSON("studio.manualRoots", state.manualRoots);
    elements.dataRootDialog.close();
    loadAccounts();
  });

  elements.groupFilters.addEventListener("click", (event) => {
    const button = event.target.closest("[data-group]");
    if (!button) return;
    state.groupFilter = button.dataset.group;
    renderGroupFilters();
    applyFilters();
  });

  elements.typeFilters.addEventListener("click", (event) => {
    const button = event.target.closest("[data-type]");
    if (!button) return;
    state.typeFilter = button.dataset.type;
    renderTypeFilters();
    applyFilters();
  });

  elements.searchInput.addEventListener("input", () => {
    state.query = elements.searchInput.value;
    applyFilters();
  });
  elements.sortSelect.addEventListener("change", () => {
    state.sort = elements.sortSelect.value;
    applyFilters();
  });
  elements.viewControls.addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (!button) return;
    state.view = button.dataset.view;
    writeStorageJSON("studio.view", state.view);
    $$("#viewControls button").forEach((node) => node.classList.toggle("active", node === button));
    renderItems();
  });
  elements.loadMoreButton.addEventListener("click", () => {
    state.renderLimit += 240;
    renderItems();
  });

  elements.itemsGrid.addEventListener("click", (event) => {
    const card = event.target.closest("[data-item-id]");
    if (!card) return;
    const itemId = card.dataset.itemId;
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (action === "toggle") {
      toggleSelected(itemId);
    } else if (action === "favorite") {
      toggleFavorite(itemId);
    } else {
      selectItem(itemId);
    }
  });
  elements.itemsGrid.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const card = event.target.closest("[data-item-id]");
    if (card) selectItem(card.dataset.itemId);
  });

  elements.selectVisibleButton.addEventListener("click", () => {
    state.filtered.forEach((item) => state.selected.add(item.id));
    renderItems();
    renderInspector();
  });
  elements.clearSelectionButton.addEventListener("click", () => {
    state.selected.clear();
    renderItems();
    renderInspector();
  });
  elements.saveButton.addEventListener("click", () => openExportDialog([...state.selected]));

  elements.previewSpeed.addEventListener("input", () => setPreviewSpeed(elements.previewSpeed.value));
  elements.previewSpeedNumber.addEventListener("change", () => {
    setPreviewSpeed(elements.previewSpeedNumber.value);
  });
  elements.previewSpeedPresets.addEventListener("click", (event) => {
    const button = event.target.closest("[data-speed]");
    if (button) setPreviewSpeed(button.dataset.speed);
  });
  elements.favoriteButton.addEventListener("click", () => {
    if (state.activeId) toggleFavorite(state.activeId);
  });
  elements.selectItemButton.addEventListener("click", () => {
    if (state.activeId) toggleSelected(state.activeId);
  });
  elements.saveItemButton.addEventListener("click", () => {
    saveCurrentConfig();
  });

  elements.exportSpeedControls.addEventListener("click", (event) => {
    const button = event.target.closest("[data-speed]");
    if (!button) return;
    state.exportSpeed = Number(button.dataset.speed);
    updateExportSpeedButtons();
  });
  elements.exportSpeedRange.addEventListener("input", () => {
    setExportSpeed(elements.exportSpeedRange.value);
  });
  elements.exportSpeedNumber.addEventListener("change", () => {
    setExportSpeed(elements.exportSpeedNumber.value);
  });
  elements.saveFolderButton.addEventListener("click", (event) => {
    event.preventDefault();
    saveToFolderPath();
  });
  elements.browserFolderButton.addEventListener("click", (event) => {
    event.preventDefault();
    saveToBrowserFolder();
  });
  elements.zipButton.addEventListener("click", (event) => {
    event.preventDefault();
    downloadZip();
  });
  elements.clearLibraryButton.addEventListener("click", clearLibrary);

  document.addEventListener("keydown", (event) => {
    const tag = document.activeElement?.tagName;
    const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
    if (event.key === "/" && !typing) {
      event.preventDefault();
      elements.searchInput.focus();
    }
    if (event.key === "Escape") {
      closeMobilePanels();
    }
  });
}

async function init() {
  mountIcons();
  initTheme();
  elements.sortSelect.value = state.sort;
  elements.itemsGrid.classList.toggle("list-view", state.view === "list");
  $$("#viewControls button").forEach((button) => button.classList.toggle("active", button.dataset.view === state.view));
  bindEvents();
  renderSummaryEmpty();
  await Promise.all([loadHealth(), loadAccounts()]);
  if (new URLSearchParams(location.search).get("demo") === "1") {
    await loadDemo();
  }
}

init();
