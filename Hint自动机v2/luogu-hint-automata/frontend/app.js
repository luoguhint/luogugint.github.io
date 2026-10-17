const state = {
  problemId: "",
  level: "concept",
  mode: "normal",
  note: "",
  pendingLevel: null,
  lastAnswer: "",
  meta: null,
  levels: [],
};

const $ = (selector) => document.querySelector(selector);
const elements = {
  form: $("#hintForm"),
  input: $("#problemId"),
  note: $("#studentNote"),
  levels: $("#levelGrid"),
  modeRow: $("#modeRow"),
  button: $("#submitBtn"),
  output: $("#output"),
  status: $("#status"),
  heroTitle: $("#heroTitle"),
  footer: $("#footer"),
};

const levelNames = {
  keyword: "关键词",
  concept: "概念铺垫",
  approach: "思路方向",
  next_step: "关键步骤",
};

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = `请求失败（${response.status}）`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (_) {
      // ignore
    }
    throw new Error(detail);
  }
  return response.json();
}

function normalizeId(value) {
  return String(value || "")
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
}

function renderLevels() {
  elements.levels.innerHTML = state.levels
    .map(
      (item) => `
      <button type="button" class="level ${item.id === state.level ? "active" : ""}" data-level="${item.id}">
        <b>${item.name}</b>
        <span>${item.goal}</span>
      </button>`
    )
    .join("");
  elements.levels.querySelectorAll(".level").forEach((button) => {
    button.addEventListener("click", () => {
      const next = button.dataset.level;
      if (next === state.level) return;
      state.pendingLevel = next;
      $("#confirmModal").classList.add("show");
      const target = state.levels.find((item) => item.id === next);
      $("#confirmLevel").textContent = target ? target.name : levelNames[next] || next;
    });
  });
}

function renderModes() {
  const modes = [
    { id: "normal", label: "常规" },
    { id: "explore", label: "探索知识点" },
    { id: "stuck", label: "我已卡住" },
  ];
  elements.modeRow.innerHTML = modes
    .map(
      (item) => `<button type="button" class="mode ${item.id === state.mode ? "active" : ""}" data-mode="${item.id}">${item.label}</button>`
    )
    .join("");
  elements.modeRow.querySelectorAll(".mode").forEach((button) => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      renderModes();
    });
  });
}

function renderMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^> (.*)$/gm, "<blockquote>$1</blockquote>")
    .replace(/^- (.*)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
    .replace(/<\/ul>\s*<ul>/g, "")
    .replace(/^\|\|(.*?)\|\|$/gm, "<hr/>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n{2,}/g, "</p><p>")
    .replace(/^(?!<[uhb]|<li|<blockquote|<hr)(.+)$/gm, "$1")
    .replace(/<\/p>\s*<h/g, "<h")
    .replace(/<\/p>\s*<ul>/g, "<ul>")
    .replace(/<\/ul>\s*<p>/g, "</ul>")
    .replace(/^/, "<p>")
    .concat("</p>")
    .replace(/<p>\s*<\/p>/g, "")
    .replace(/<p>(<h[23]>)/g, "$1")
    .replace(/(<\/h[23]>)<\/p>/g, "$1")
    .replace(/<p>(<blockquote>)/g, "$1")
    .replace(/(<\/blockquote>)<\/p>/g, "$1")
    .replace(/<p>\s*<hr\/>\s*<\/p>/g, "<hr/>")
    .replace(/<p>(<ul>)/g, "$1")
    .replace(/(<\/ul>)<\/p>/g, "$1")
    .replace(/<\/ul><ul>/g, "");
}

function renderSkeleton() {
  elements.output.innerHTML = `
    <div class="stage">生成中</div>
    <h3>正在为你整理提示…</h3>
    <div class="skeleton"><span style="width:96%"></span><span style="width:88%"></span><span style="width:72%"></span><span style="width:60%"></span></div>`;
}

function renderError(message) {
  elements.output.innerHTML = `<div class="error">⚠️ ${message}</div>`;
}

function renderResult(data) {
  const safety = data.safety || {};
  const badges = [
    `<span class="badge">${levelNames[data.level] || data.level}</span>`,
    `<span class="badge">${data.model || "demo"}</span>`,
  ];
  if (data.demo) badges.push(`<span class="badge warn">演示模式：未接入真实模型</span>`);
  if (safety.safe === false) badges.push(`<span class="badge bad">已触发内容审查</span>`);
  else badges.push(`<span class="badge good">已通过反剧透审查</span>`);

  const sources = (data.sources || [])
    .map((item) => `<li>${escapeHtml(item.title)}｜${escapeHtml(item.author || "未知")}｜${item.votes || 0} 赞</li>`)
    .join("");

  const next = data.suggested_next_level
    ? `<div class="next"><button type="button" class="btn" id="nextLevelBtn">再深入一点：${levelNames[data.suggested_next_level] || data.suggested_next_level}</button><button type="button" class="btn ghost" id="copyBtn">复制提示</button></div>`
    : `<div class="next"><button type="button" class="btn ghost" id="copyBtn">复制提示</button></div>`;

  elements.output.innerHTML = `
    <div class="output-head">
      <div><div class="stage">${data.problem_id} · ${escapeHtml(data.title)}</div><h3>Hint 已生成</h3>
      <div class="badges">${badges.join("")}</div></div>
    </div>
    <div class="answer">${renderMarkdown(data.answer)}</div>
    ${sources ? `<div class="sources"><b>参考来源</b><ul>${sources}</ul></div>` : ""}
    ${next}
    <p class="note">建议先在纸上完成一步，再继续查看下一档；直接阅读完整题解会削弱训练效果。</p>`;

  state.lastAnswer = data.answer;
  $("#nextLevelBtn")?.addEventListener("click", () => {
    if (!data.suggested_next_level) return;
    state.level = data.suggested_next_level;
    state.pendingLevel = null;
    renderLevels();
    requestHint(true);
  });
  $("#copyBtn")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(data.answer.replace(/[#*>-]/g, "").trim());
      const button = $("#copyBtn");
      const original = button.textContent;
      button.textContent = "已复制";
      setTimeout(() => (button.textContent = original), 1600);
    } catch (_) {
      // ignore
    }
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

async function loadHealth() {
  try {
    const data = await fetchJSON("/api/health");
    elements.status.innerHTML = `<span class="dot"></span>服务正常 · v${data.version} · 模型 ${data.model}`;
  } catch (error) {
    elements.status.innerHTML = `<span class="dot" style="background:var(--warn)"></span>后端连接失败，请先运行后端服务`;
  }
}

async function requestHint(skipConfirm = false) {
  const problemId = normalizeId(elements.input.value);
  if (!problemId) {
    renderError("请输入洛谷题号，例如 P1001。");
    return;
  }
  state.problemId = problemId;
  elements.input.value = problemId;
  elements.button.disabled = true;
  renderSkeleton();
  try {
    const result = await fetchJSON("/api/hint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        problem_id: problemId,
        level: state.level,
        mode: state.mode,
        student_note: state.note,
      }),
    });
    state.meta = result;
    renderResult(result);
    if (!skipConfirm) {
      elements.heroTitle.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (error) {
    renderError(error.message || "生成失败，请稍后重试。");
  } finally {
    elements.button.disabled = false;
  }
}

function bindConfirmModal() {
  $("#confirmYes").addEventListener("click", () => {
    if (state.pendingLevel) state.level = state.pendingLevel;
    $("#confirmModal").classList.remove("show");
    state.pendingLevel = null;
    renderLevels();
    requestHint();
  });
  $("#confirmNo").addEventListener("click", () => {
    state.pendingLevel = null;
    $("#confirmModal").classList.remove("show");
  });
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  state.note = elements.note.value;
  requestHint();
});

(async function init() {
  try {
    const data = await fetchJSON("/api/levels");
    state.levels = data.levels;
  } catch (_) {
    state.levels = [
      { id: "keyword", name: "关键词提示", goal: "只提示可能相关的知识点" },
      { id: "concept", name: "概念铺垫", goal: "补齐知识，不建立本题模型" },
      { id: "approach", name: "思路方向", goal: "收窄思路，不给完整做法" },
      { id: "next_step", name: "关键步骤", goal: "突破当前卡点" },
    ];
  }
  renderLevels();
  renderModes();
  bindConfirmModal();
  loadHealth();
  elements.footer.innerHTML = `Hint Automata v2.0 · 题面与题解来源洛谷；生成内容仅供参考，侵权可联系删除。`;
})();
