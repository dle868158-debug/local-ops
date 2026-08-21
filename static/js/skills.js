'use strict';
/* ============================================================
   skills.js — 技能工作台视图
   · 懒加载 GET /api/skills（仅视图激活时拉取，缓存于内存）
   · 概览统计 + 分类 / 技能库筛选 + 中文搜索
   · 卡片网格（中文简介 / 分类 / 来源徽标）+ 详情抽屉
   ============================================================ */
import { $, el, setText, setChildren, icon, escapeHtml, toast, openLayer, closeLayer } from './core.js';

const ROOT_LABELS = { agents: 'AI', claude: 'Claude', codex: 'Codex' };

let snapshot = null;   // /api/skills 响应
let loading = false;
let dirty = true;      // 数据或筛选变化后需要重绘
let loadController = null;
let loadFailed = false;      // 最近一次自动加载失败，用于抑制轮询错误提示风暴
let lastLoadFailAt = 0;      // 上次失败时间戳，自动重试冷却
let query = '';
let category = '全部';
let rootFilter = '全部';
const LOAD_RETRY_MS = 30000; // 自动加载失败后的冷却时长

const grid = $('#skGrid');
const empty = $('#skEmpty');
const searchInput = $('#skSearch');
const catChips = $('#skCatChips');
const rootChips = $('#skRootChips');
const drawerMask = $('#skDrawerMask');
const drawer = $('#skDrawer');
const drawerBody = $('#skDrawerBody');

function rootLabel(id) { return ROOT_LABELS[id] || id; }

/* 把任意字符串转成安全、唯一的 DOM id/class token（去掉危险字符 + 空格 → 中划线） */
function safeToken(value) {
  return String(value || '').trim()
    .replace(/[^\w\u4e00-\u9fa5-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

/* ---------------- 数据 ---------------- */
async function loadSkills(force = false) {
  if (loading) return;
  if (!force && snapshot) { dirty = true; return; }
  loading = true;
  const status = $('#skLoadStatus');
  if (status) status.textContent = force ? '正在局部刷新技能…' : '正在加载技能…';
  loadController = new AbortController();
  const timer = setTimeout(() => loadController.abort(), 12000);
  try {
    const r = await fetch('/api/skills', { cache: 'no-store', signal: loadController.signal });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const next = await r.json();
    if (!next || !Array.isArray(next.skills)) throw new Error('技能数据格式无效');
    /* 规范化：保证 roots/categories 为数组，避免非数组时渲染崩溃 */
    next.skills = next.skills.filter(s => s && typeof s === 'object');
    if (!Array.isArray(next.roots)) next.roots = [];
    if (!Array.isArray(next.categories)) next.categories = [];
    snapshot = next;
    dirty = true;
    loadFailed = false;
    if (status) status.textContent = '已显示全部 ' + next.count + ' 个技能';
  } catch (e) {
    const msg = e.name === 'AbortError' ? '加载超时，请稍后重试' : (e.message || e);
    if (status) status.textContent = '技能加载失败：' + msg;
    /* 只在用户主动刷新（force）或首次自动失败时提示，避免每次主轮询都弹错 */
    if (force || !loadFailed) toast('技能清单加载失败：' + msg);
    loadFailed = true;
    lastLoadFailAt = Date.now();
  } finally {
    clearTimeout(timer);
    loadController = null;
    loading = false;
  }
}

function refreshSkills() {
  if (loading) return;
  const btn = $('#skRefresh');
  const label = btn && btn.querySelector('.sk-refresh-label');
  if (btn) btn.disabled = true;
  if (label) label.textContent = '刷新中…';
  loadSkills(true).then(() => {
    if (snapshot) {
      renderSkills();   // 立即重绘，不必等下一次主轮询
      toast('技能区域已刷新（共 ' + snapshot.count + ' 个）');
    }
  }).finally(() => {
    if (btn) btn.disabled = false;
    if (label) label.textContent = '刷新技能';
  });
}

/* ---------------- 对外入口（app.js 轮询 / 切视图时调用） ---------------- */
export function renderSkills() {
  const active = $('#view-skills').classList.contains('active');
  if (!active) return;
  /* 自动加载仅在：无数据，或加载失败且已过冷却期（避免错误提示风暴） */
  if (!snapshot && !loading &&
      (!loadFailed || Date.now() - lastLoadFailAt > LOAD_RETRY_MS)) {
    loadSkills();
  }
  if (snapshot && dirty) {
    dirty = false;
    renderAll();
  }
}

/* ---------------- 全量渲染 ---------------- */
function renderAll() {
  renderStats();
  renderChips();
  renderGrid();
}

/* ---------------- 概览统计 ---------------- */
function renderStats() {
  const skills = Array.isArray(snapshot.skills) ? snapshot.skills : [];
  const zhCount = skills.filter(s => s && s.hasZh).length;
  const roots = Array.isArray(snapshot.roots) ? snapshot.roots : [];
  const total = Number.isInteger(snapshot.count) ? snapshot.count : skills.length;
  setText($('#skStatTotal'), String(total));
  setText($('#skStatTotalSub'), '来自 ' + roots.length + ' 个技能库');
  setText($('#skStatCats'), String((snapshot.categories || []).length));
  setText($('#skStatZh'), String(zhCount));
  setText($('#skStatZhSub'), zhCount === skills.length
    ? '全部技能已有中文解读' : (skills.length - zhCount) + ' 个暂无中文');
  setText($('#skStatRoots'), String(roots.length));
  setText($('#skStatRootsSub'), roots.map(r => r.label).join(' · '));
  setText($('#navCountSkills'), total ? String(total) : '');
  const list = $('#skRootsList');
  setChildren(list, ...(roots.map((r, i) => {
    const row = el('div', 't5-row');
    const rank = el('span', 't5-rank');
    rank.textContent = String(i + 1);
    const name = el('span', 't5-name');
    name.textContent = r.label;
    const val = el('span', 't5-val');
    val.textContent = r.count + ' 个';
    row.append(rank, name, val);
    return row;
  })));
  setChildren($('#skTipIcon'), icon('brain', 14));
}

/* ---------------- 筛选 ---------------- */
function renderChips() {
  /* 刷新后校正筛选状态：若当前分类/技能库已不在新快照中，重置为「全部」 */
  const categories = Array.isArray(snapshot.categories) ? snapshot.categories : [];
  if (category !== '全部' && !categories.includes(category)) category = '全部';
  const rootIds = (Array.isArray(snapshot.roots) ? snapshot.roots : [])
    .map(r => r.id);
  if (rootFilter !== '全部' && !rootIds.includes(rootFilter)) rootFilter = '全部';
  renderChipRow(catChips, ['全部', ...categories], category, v => {
    category = v; dirty = true; renderSkills();
  });
  renderChipRow(rootChips, ['全部', ...rootIds], rootFilter, v => {
    rootFilter = v; dirty = true; renderSkills();
  });
}

function renderChipRow(row, values, current, onPick) {
  row.replaceChildren();
  values.forEach(v => {
    const btn = el('button', 'fchip' + (v === current ? ' active' : ''));
    btn.type = 'button';
    btn.textContent = v === '全部' ? '全部' : (row === catChips ? v : rootLabel(v));
    btn.setAttribute('aria-pressed', String(v === current));
    btn.addEventListener('click', () => onPick(v));
    row.appendChild(btn);
  });
}

function matchSkill(s) {
  if (category !== '全部' && s.category !== category) return false;
  if (rootFilter !== '全部' && !(s.roots || []).includes(rootFilter)) return false;
  if (query) {
    const hay = [s.id, s.dir, s.summary, s.detail, s.usage,
      s.description, (s.triggers || []).join(' ')]
      .join(' ').toLowerCase();
    if (!hay.includes(query)) return false;
  }
  return true;
}

/* ---------------- 卡片网格 ---------------- */
function renderGrid() {
  const skills = (snapshot.skills || []).filter(matchSkill);
  setText($('#skCount'), '共 ' + skills.length + ' 个');
  empty.hidden = skills.length > 0;
  if (skills.length === 0) {
    /* 空态：区分「无技能」vs「搜索/筛选无匹配」，并提供清除入口 */
    const hasFilter = !!query || category !== '全部' || rootFilter !== '全部';
    setText($('#skEmptyText'), hasFilter ? '没有匹配的技能，换个关键词试试' : '技能库为空，暂无可用技能');
    const clear = $('#skEmptyClear');
    if (clear) clear.hidden = !hasFilter;
  }
  grid.replaceChildren();
  const grouped = new Map();
  skills.forEach(s => {
    const key = s.category || '其他';
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(s);
  });
  [...grouped.entries()].forEach(([cat, items]) => {
    const section = el('section', 'sk-category');
    const catToken = safeToken(cat) || 'other';
    section.setAttribute('aria-labelledby', 'sk-cat-' + catToken);
    const head = el('div', 'sk-category-head');
    const title = el('h3', 'sk-category-title');
    title.id = 'sk-cat-' + catToken;
    title.textContent = cat;
    const count = el('span', 'sk-category-count');
    count.textContent = items.length + ' 个技能';
    head.append(title, count);
    const cards = el('div', 'sk-category-grid');
    items.forEach(s => cards.appendChild(buildCard(s)));
    section.append(head, cards);
    grid.appendChild(section);
  });
}

function buildCard(s) {
  const card = el('article', 'sk-card');
  card.setAttribute('role', 'listitem');

  const top = el('div', 'sk-card-top');
  const name = el('span', 'sk-name');
  name.textContent = s.id;
  name.title = s.id;   // 截断时悬停显示完整技能名
  const cat = el('span', 'sk-badge');
  cat.textContent = s.category;
  top.append(name, cat);
  const call = el('button', 'sk-call');
  call.type = 'button';
  call.textContent = '调用技能';
  call.setAttribute('aria-label', '调用 ' + s.id);
  call.addEventListener('click', () => openCallPanel(s));
  top.appendChild(call);

  const body = el('div', 'sk-card-body');
  const summary = el('p', 'sk-summary');
  /* 中文简介截断到合理长度，防超长文本撑爆卡片；省略号用 title 补全 */
  const sumText = String(s.summary || s.description || '暂无说明');
  summary.textContent = sumText.length > 90 ? sumText.slice(0, 90) + '…' : sumText;
  if (sumText.length > 90) summary.title = sumText;
  if (!s.hasZh) summary.classList.add('no-zh');
  body.appendChild(summary);

  const meta = el('div', 'sk-card-meta');
  (s.roots || []).forEach(rid => {
    const b = el('span', 'sk-root sk-root-' + safeToken(rid));
    b.textContent = rootLabel(rid);
    b.title = rid === 'agents' ? 'AI 技能库' : rid === 'claude' ? 'Claude 技能库' : 'Codex 技能库';
    meta.appendChild(b);
  });
  if (s.version) {
    const v = el('span', 'sk-ver mono');
    v.textContent = 'v' + s.version;
    meta.appendChild(v);
  }
  if (!s.hasZh) {
    const nz = el('span', 'sk-nozh');
    nz.textContent = '暂无中文';
    meta.appendChild(nz);
  }
  if (s.updated) {
    const up = el('span', 'sk-upd mono');
    up.textContent = s.updated;
    meta.appendChild(up);
  }
  const detailBtn = el('button', 'sk-detail-link');
  detailBtn.type = 'button';
  detailBtn.textContent = '查看完整说明 →';
  detailBtn.addEventListener('click', () => openDrawer(s));

  card.append(top, body, meta, detailBtn);
  return card;
}

/* ---------------- 详情抽屉 ---------------- */
function openDrawer(s) {
  if (!s) return;
  setText($('#skDrawerTitle'), s.id);
  setChildren(drawerBody, buildDetail(s));
  /* 用 core 的 openLayer：自动 shell inert + 记录/恢复触发焦点 */
  openLayer(drawer, () => drawer.querySelector('#skDrawerClose'));
  drawerMask.classList.add('open');
  drawerMask.setAttribute('aria-hidden', 'false');
}

function buildCallPanel(s) {
  const wrap = el('div', 'sk-call-panel');
  const intro = el('p', 'skd-summary');
  intro.textContent = '点击复制后，把这句话发送给当前 AI，即可调用该技能。';
  const prompt = el('textarea', 'sk-call-prompt');
  prompt.readOnly = true;
  prompt.rows = 5;
  prompt.value = '请调用「' + s.id + '」技能。\n\n我需要：';
  prompt.setAttribute('aria-label', '技能调用语句');
  const actions = el('div', 'sk-call-actions');
  const copy = el('button', 'btn btn-primary');
  copy.type = 'button';
  copy.textContent = '复制调用语句';
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(prompt.value);
      toast('调用语句已复制');
    } catch (e) {
      /* 剪贴板 API 失败兜底：选中文本 + execCommand('copy')，HTTP 环境也能复制 */
      prompt.focus(); prompt.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch (e2) { copied = false; }
      if (copied) toast('调用语句已复制');
      else toast('已选中调用语句，请按 Ctrl+C 复制');
    }
  });
  const detail = el('button', 'btn');
  detail.type = 'button';
  detail.textContent = '查看技能说明';
  detail.addEventListener('click', () => openDrawer(s));
  actions.append(copy, detail);
  wrap.append(intro, block('推荐调用语句', [prompt]), actions);
  return wrap;
}

function openCallPanel(s) {
  setText($('#skDrawerTitle'), '调用技能 · ' + s.id);
  setChildren(drawerBody, buildCallPanel(s));
  openLayer(drawer, () => drawer.querySelector('#skDrawerClose'));
  drawerMask.classList.add('open');
  drawerMask.setAttribute('aria-hidden', 'false');
}

export function closeSkillDrawer() {
  closeLayer(drawer);
  drawerMask.classList.remove('open');
  drawerMask.setAttribute('aria-hidden', 'true');
}

function metaRow(label, value, mono) {
  const row = el('div', 'skd-meta-row');
  const l = el('span', 'skd-meta-label');
  l.textContent = label;
  const v = el('span', 'skd-meta-value' + (mono ? ' mono' : ''));
  /* 长字段（路径/仓库等）截断显示，悬停 title 补全 */
  const raw = value || '—';
  const text = String(raw);
  v.textContent = text.length > 40 ? text.slice(0, 40) + '…' : text;
  if (text.length > 40) v.title = text;
  row.append(l, v);
  return row;
}

function block(title, children) {
  const sec = el('div', 'skd-block');
  const h = el('h4', 'skd-block-title');
  h.textContent = title;
  sec.appendChild(h);
  children.forEach(c => sec.appendChild(c));
  return sec;
}

function buildDetail(s) {
  const wrap = el('div', 'skd');
  const head = el('div', 'skd-head');
  const name = el('h3', 'skd-name');
  name.textContent = s.id;
  const cat = el('span', 'sk-badge');
  cat.textContent = s.category;
  head.append(name, cat);
  wrap.appendChild(head);

  const roots = el('div', 'skd-roots');
  (s.roots || []).forEach(rid => {
    const b = el('span', 'sk-root sk-root-' + safeToken(rid));
    b.textContent = rootLabel(rid);
    roots.appendChild(b);
  });
  wrap.appendChild(roots);

  if (s.summary) {
    const sum = el('p', 'skd-summary');
    sum.textContent = s.summary;
    wrap.appendChild(sum);
  }
  if (!s.hasZh) {
    const warn = el('p', 'skd-warn');
    warn.textContent = '该技能暂无中文说明，以下展示技能自带描述。';
    wrap.appendChild(warn);
  }
  if (s.detail) {
    wrap.appendChild(block('它能做什么', [paragraph(s.detail)]));
  }
  if (s.usage) {
    wrap.appendChild(block('什么时候用', [paragraph(s.usage)]));
  }
  const trigs = (s.triggers || []).filter(Boolean);
  if (trigs.length) {
    const chips = el('div', 'skd-chips');
    trigs.forEach(t => {
      const c = el('span', 'skd-chip');
      c.textContent = t;
      chips.appendChild(c);
    });
    wrap.appendChild(block('触发方式（对这些话它会自动激活）', [chips]));
  }
  if (s.description) {
    const pre = el('p', 'skd-orig');
    pre.textContent = s.description;
    wrap.appendChild(block('原始英文描述', [pre]));
  }
  const meta = el('div', 'skd-meta');
  meta.appendChild(metaRow('版本', s.version ? 'v' + s.version : '', true));
  meta.appendChild(metaRow('更新时间', s.updated, true));
  meta.appendChild(metaRow('来源仓库', s.source, true));
  meta.appendChild(metaRow('安装时间', s.installedAt, true));
  meta.appendChild(metaRow('文件位置', s.path, true));
  wrap.appendChild(block('元信息', [meta]));

  const related = (s.related || []).filter(Boolean);
  if (related.length) {
    const chips = el('div', 'skd-chips');
    related.forEach(r => {
      const c = el('button', 'skd-chip skd-chip-link');
      c.type = 'button';
      c.textContent = r;
      c.addEventListener('click', () => {
        const target = (snapshot.skills || []).find(x => x.id === r);
        if (target) openDrawer(target);
        else toast('未找到关联技能「' + r + '」，可能未安装');
      });
      chips.appendChild(c);
    });
    wrap.appendChild(block('关联技能', [chips]));
  }
  return wrap;
}

function paragraph(text) {
  const p = el('p', 'skd-text');
  p.textContent = text;
  return p;
}

/* ---------------- 事件绑定 ---------------- */
/* 搜索防抖：避免每敲一字就全量重渲染（118 张卡片），200ms 合并输入 */
let searchTimer = null;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    query = searchInput.value.trim().toLowerCase();
    dirty = true;
    renderSkills();
  }, 200);
});

/* 空态「清除搜索条件」：重置搜索 + 筛选为全部 */
$('#skEmptyClear').addEventListener('click', () => {
  searchInput.value = '';
  query = '';
  category = '全部';
  rootFilter = '全部';
  dirty = true;
  renderSkills();
  searchInput.focus();
});

$('#skRefresh').addEventListener('click', refreshSkills);

$('#skDrawerClose').addEventListener('click', closeSkillDrawer);
drawerMask.addEventListener('mousedown', e => {
  if (e.target === drawerMask) closeSkillDrawer();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && drawer.classList.contains('open')) {
    e.stopPropagation();
    closeSkillDrawer();
  }
});
