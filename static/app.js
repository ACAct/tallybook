/* 轻记界面：所有用户内容通过 textContent 渲染，金额始终以整数分参与计算。 */
'use strict';
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { view: 'overview', data: null, filters: {}, page: 1, editing: null, sequence: 0, money: {} };
const palette = ['#78996b', '#a7bb8e', '#d4b687', '#9eb5b0', '#c5ccba', '#e4d5ba'];
const money = (cents) => (cents / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const currency = (cents) => `¥ ${money(cents)}`;
const localDate = (date = new Date()) => `${String(date.getFullYear()).padStart(4, '0')}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const chartColors = () => document.documentElement.dataset.theme === 'dark'
  ? { grid: '#2c3832', label: '#8b968f', axis: '#8b968f', income: '#7fb398', expense: '#d9a06b' }
  : { grid: '#edf0e8', label: '#a2ac97', axis: '#98a48d', income: '#7da183', expense: '#dec39a' };
function animateMoney(element, targetCents, key) {
  const from = state.money[key] ?? 0;
  state.money[key] = targetCents;
  if (reducedMotion()) { element.textContent = currency(targetCents); return; }
  const start = performance.now();
  const duration = 450;
  function tick(now) {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    element.textContent = currency(Math.round(from + (targetCents - from) * eased));
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const icon = $('#theme-toggle use');
  if (icon) icon.setAttribute('href', theme === 'dark' ? '#i-sun' : '#i-moon');
  try { localStorage.setItem('qingji-theme', theme); } catch { /* 隐私模式下忽略 */ }
}
function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem('qingji-theme'); } catch { saved = null; }
  applyTheme(saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function svgElement(tag, attributes = {}, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
  if (text !== undefined) node.textContent = text;
  return node;
}
function icon(name) {
  const svg = svgElement('svg', { 'aria-hidden': 'true' });
  svg.append(svgElement('use', { href: `#i-${name}` }));
  return svg;
}
function showError(target, message) {
  target.textContent = message || '';
  target.hidden = !message;
}
let toastTimer;
function toast(message) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 3800);
}
async function request(path, options = {}) {
  let response;
  try { response = await fetch(path, options); }
  catch { throw new Error('无法连接本地服务，请确认运行窗口仍然打开，再重试。'); }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || '操作失败，请重试');
  return data;
}
const jsonOptions = (method, data) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
function currentFilters() {
  return Object.fromEntries([...new FormData($('#filter-form')).entries()].filter(([, value]) => value !== ''));
}
async function refresh(filters = state.filters) {
  const sequence = ++state.sequence;
  $('#save-status').textContent = '正在读取本地账本…';
  try {
    const data = await request(`/api/dashboard?${new URLSearchParams(filters)}`);
    if (sequence !== state.sequence) return false;
    state.filters = { ...filters };
    state.data = data;
    showError($('#page-error'), '');
    render();
    $('#save-status').textContent = '已与本地账本同步';
    return true;
  } catch (error) {
    if (sequence !== state.sequence) return false;
    showError($('#page-error'), error.message);
    $('#save-status').textContent = '同步失败，请检查运行窗口';
    $('#results-label').textContent = '读取失败，点击“筛选”重试';
    return false;
  }
}
function render() {
  const { records, summary, categories, total_count: total } = state.data;
  $('#nav-count').textContent = total.toLocaleString('zh-CN');
  $('#results-label').textContent = `共 ${records.length} 笔记录`;
  $('#filter-label').textContent = Object.keys(state.filters).length ? '正在查看筛选结果' : '查看全部收支';
  animateMoney($('#balance-total'), summary.balance_cents, 'balance');
  animateMoney($('#income-total'), summary.income_cents, 'income');
  animateMoney($('#expense-total'), summary.expense_cents, 'expense');
  const incomeCount = records.filter(row => row.type === 'income').length;
  $('#income-count').textContent = `${incomeCount} 笔收入`;
  $('#expense-count').textContent = `${records.length - incomeCount} 笔支出`;
  const categoryValue = $('#filter-category').value;
  $('#filter-category').replaceChildren(new Option('全部类别', ''));
  const categoryList = [...new Set([...categories, categoryValue].filter(Boolean))];
  categoryList.forEach(value => $('#filter-category').add(new Option(value, value)));
  $('#filter-category').value = categoryValue;
  renderRecords();
  renderTrend(summary);
  renderCategories(summary);
  renderAnalysis(summary);
}
function changeView(view) {
  state.view = view;
  state.page = 1;
  const titles = { overview: ['账本总览', '记录生活的点滴，让收支一目了然。'], records: ['全部记录', '翻开账本，找到每一笔生活的足迹。'], analysis: ['收支分析', '从数字里，看见自己的生活节奏。'] };
  $('#page-title').textContent = titles[view][0];
  $('#page-subtitle').textContent = titles[view][1];
  $$('.nav-item').forEach(button => {
    const active = button.dataset.view === view;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  $('#charts-section').hidden = view === 'records';
  $('#records-section').hidden = view === 'analysis';
  $('#analysis-details').hidden = view !== 'analysis';
  $('#view-all').hidden = view !== 'overview';
  $('#records-title').textContent = view === 'overview' ? '最近记录' : '全部记录';
  $('#records-subtitle').textContent = view === 'overview' ? '按记账日期倒序，展示最近 8 笔' : '按记账日期倒序，每页 12 笔';
  if (state.data) renderRecords();
}
function recordSymbol(category, type) {
  return ({ 餐饮: '食', 交通: '行', 购物: '购', 居住: '居', 娱乐: '乐', 医疗: '医', 学习: '学', 工资: '薪', 奖金: '奖', 兼职: '兼', 理财: '财', 礼金: '礼' })[category] || (type === 'income' ? '入' : '支');
}
function renderRecords() {
  const rows = state.data.records;
  const size = state.view === 'overview' ? 8 : 12;
  const maxPage = Math.max(1, Math.ceil(rows.length / size));
  state.page = Math.min(state.page, maxPage);
  const displayRows = rows.slice((state.page - 1) * size, state.page * size);
  const body = $('#records-body');
  body.replaceChildren();
  for (const row of displayRows) {
    const tr = element('tr');
    const categoryCell = element('td');
    const category = element('div', 'record-category');
    const badge = element('span', 'category-badge', recordSymbol(row.category, row.type));
    if (row.type === 'income') { badge.style.background = '#ecf3e8'; badge.style.color = '#709268'; }
    const info = element('div', 'category-info');
    info.append(element('strong', '', row.category));
    const note = element('small', '', row.note || '无备注');
    note.title = row.note;
    info.append(note); category.append(badge, info); categoryCell.append(category);
    const dateCell = element('td', '', row.date.replaceAll('-', '.'));
    const typeCell = element('td');
    typeCell.append(element('span', `type-pill ${row.type}`, row.type === 'income' ? '收入' : '支出'));
    const amountCell = element('td', `amount-cell amount-value ${row.type === 'income' ? 'income-text' : 'expense-text'}`, `${row.type === 'income' ? '+' : '−'} ${money(row.amount_cents)}`);
    const operations = element('td', 'operation-cell');
    const edit = element('button', 'icon-button');
    edit.setAttribute('aria-label', `编辑 ${row.category} ${money(row.amount_cents)} 元`); edit.title = '编辑'; edit.append(icon('edit'));
    edit.addEventListener('click', () => openRecord(row));
    const remove = element('button', 'icon-button danger');
    remove.setAttribute('aria-label', `删除 ${row.category} ${money(row.amount_cents)} 元`); remove.title = '删除'; remove.append(icon('trash'));
    remove.addEventListener('click', () => deleteRecord(row));
    operations.append(edit, remove); tr.append(categoryCell, dateCell, typeCell, amountCell, operations); body.append(tr);
  }
  $('#records-empty').hidden = rows.length > 0;
  const filtered = Object.keys(state.filters).length > 0;
  $('#empty-title').textContent = filtered ? '没有找到符合条件的记录' : '从第一笔记录开始';
  $('#empty-copy').textContent = filtered ? '试试调整日期、类别或金额范围。' : '一杯咖啡，一份收入，都值得记下来。';
  $('#empty-add').hidden = filtered;
  $('#pagination').hidden = state.view === 'overview' || rows.length <= size;
  $('#page-info').textContent = `第 ${state.page} / ${maxPage} 页 · 共 ${rows.length} 笔`;
  $('#prev-page').disabled = state.page === 1;
  $('#next-page').disabled = state.page === maxPage;
}
function chartEmpty(container, message) {
  const empty = element('div', 'chart-empty');
  empty.append(icon('chart'), element('span', '', message));
  container.replaceChildren(empty);
}
function renderTrend(summary) {
  const container = $('#trend-chart');
  const colors = chartColors();
  if (!summary.months.length) return chartEmpty(container, '记下第一笔收支，趋势就从这里开始');
  const source = new Map(summary.months.map(row => [row.month, row]));
  const last = summary.months.at(-1).month;
  const [year, month] = last.split('-').map(Number);
  const lastIndex = year * 12 + month - 1;
  const [firstYear, firstMonth] = summary.months[0].month.split('-').map(Number);
  const firstIndex = Math.max(firstYear * 12 + firstMonth - 1, lastIndex - 11);
  const series = [];
  for (let index = firstIndex; index <= lastIndex; index++) {
    const key = `${String(Math.floor(index / 12)).padStart(4, '0')}-${String(index % 12 + 1).padStart(2, '0')}`;
    series.push(source.get(key) || { month: key, income_cents: 0, expense_cents: 0 });
  }
  $('#trend-subtitle').textContent = lastIndex - (firstYear * 12 + firstMonth - 1) >= 12 ? '展示筛选结果最近 12 个月' : '按月看看钱的来去';
  const svg = svgElement('svg', { viewBox: '0 0 540 184', role: 'img', 'aria-label': '按月收入与支出柱状图' });
  svg.append(svgElement('title', {}, '月度收支：' + series.map(row => `${row.month} 收入 ${money(row.income_cents)} 元，支出 ${money(row.expense_cents)} 元`).join('；')));
  const max = Math.max(...series.flatMap(row => [row.income_cents, row.expense_cents]), 100);
  const unit = 10 ** Math.floor(Math.log10(max));
  const top = Math.ceil(max / unit) * unit;
  for (let i = 0; i <= 3; i++) {
    const y = 12 + i * 44;
    svg.append(svgElement('line', { x1: 52, x2: 534, y1: y, y2: y, stroke: colors.grid, 'stroke-dasharray': '3 4' }));
    const amount = top * (3 - i) / 3 / 100;
    const label = amount >= 10000 ? `${+(amount / 10000).toFixed(1)}万` : `${+amount.toFixed(amount < 10 ? 2 : 0)}`;
    svg.append(svgElement('text', { x: 43, y: y + 3, fill: colors.label, 'font-size': 9, 'text-anchor': 'end' }, label));
  }
  const step = 476 / series.length;
  const barWidth = Math.min(26, step * .25);
  series.forEach((row, index) => {
    const center = 55 + step * (index + .5);
    for (const [key, offset, fill] of [['income_cents', -barWidth - 2, colors.income], ['expense_cents', 2, colors.expense]]) {
      const height = row[key] / top * 132;
      const rect = svgElement('rect', { x: center + offset, y: 144 - height, width: barWidth, height, rx: 3, fill });
      rect.append(svgElement('title', {}, `${row.month} ${key === 'income_cents' ? '收入' : '支出'}：${currency(row[key])}`));
      svg.append(rect);
    }
    svg.append(svgElement('text', { x: center, y: 166, fill: colors.axis, 'font-size': 9, 'text-anchor': 'middle' }, series.length > 6 ? row.month.slice(5) + '月' : row.month));
  });
  container.replaceChildren(svg);
}
function renderCategories(summary) {
  const container = $('#category-chart');
  if (!summary.expense_cents) return chartEmpty(container, '当前范围暂无支出');
  const sorted = summary.categories.filter(row => row.expense_cents).sort((a, b) => b.expense_cents - a.expense_cents);
  const series = sorted.slice(0, 5);
  if (sorted.length > 5) series.push({ category: '其余类别', expense_cents: sorted.slice(5).reduce((sum, row) => sum + row.expense_cents, 0) });
  let angle = 0;
  const gradient = series.map((row, i) => {
    const from = angle; angle += row.expense_cents / summary.expense_cents * 360;
    return `${palette[i]} ${from}deg ${angle}deg`;
  });
  const donut = element('div', 'donut');
  donut.style.background = `conic-gradient(${gradient.join(',')})`;
  donut.setAttribute('role', 'img');
  donut.setAttribute('aria-label', `支出总计 ${money(summary.expense_cents)} 元，各类别见旁侧列表`);
  const inside = element('div', 'donut-inner');
  inside.append(element('span', '', '总支出'), element('strong', '', currency(summary.expense_cents))); donut.append(inside);
  const legend = element('div', 'category-legend');
  series.forEach((row, index) => {
    const line = element('div', 'category-row');
    const dot = element('i'); dot.style.background = palette[index];
    const name = element('span', 'category-name', row.category); name.title = row.category;
    line.append(dot, name, element('span', 'percent', `${(row.expense_cents / summary.expense_cents * 100).toFixed(1)}%`), element('strong', '', money(row.expense_cents)));
    legend.append(line);
  });
  container.replaceChildren(donut, legend);
}
function renderAnalysis(summary) {
  const body = $('#analysis-body'); body.replaceChildren();
  for (const row of summary.categories) {
    const tr = element('tr');
    tr.append(element('td', '', row.category), element('td', '', row.count), element('td', 'amount-cell income-text', currency(row.income_cents)), element('td', 'amount-cell', currency(row.expense_cents)), element('td', 'amount-cell', currency(row.income_cents - row.expense_cents)));
    body.append(tr);
  }
  if (!summary.count) { const tr = element('tr'); const td = element('td', '', '当前范围暂无记录，调整筛选或记下第一笔。'); td.colSpan = 5; tr.append(td); body.append(tr); }
}
function updateCategorySuggestions(kind) {
  const defaults = state.data?.defaults[kind] || (kind === 'income' ? ['工资', '奖金', '兼职'] : ['餐饮', '交通', '购物']);
  const names = [...new Set([...defaults, ...(state.data?.categories || [])])];
  $('#category-options').replaceChildren(...names.map(name => new Option(name, name)));
  return defaults[0];
}
function openRecord(row = null) {
  state.editing = row?.id || null;
  $('#record-form').reset();
  $('#dialog-title').textContent = row ? '编辑记录' : '记一笔';
  const kind = row?.type || 'expense';
  $(`#record-form input[value="${kind}"]`).checked = true;
  $('#record-category').value = row?.category || updateCategorySuggestions(kind);
  updateCategorySuggestions(kind);
  $('#record-date').value = row?.date || localDate();
  $('#record-amount').value = row ? (row.amount_cents / 100).toFixed(2) : '';
  $('#record-note').value = row?.note || '';
  showError($('#form-error'), '');
  $('#record-dialog').showModal();
  $('#record-amount').focus();
}
async function saveRecord(event) {
  event.preventDefault();
  if (!$('#record-form').reportValidity()) return;
  const payload = Object.fromEntries(new FormData($('#record-form')));
  const button = $('#save-record'); button.disabled = true; button.textContent = '正在保存…';
  try {
    const editId = state.editing;
    await request(editId ? `/api/records/${editId}` : '/api/records', jsonOptions(editId ? 'PUT' : 'POST', payload));
    $('#record-dialog').close();
    const loaded = await refresh();
    const visible = state.data?.records.some(row => editId ? row.id === editId : row.date === payload.date && row.category === payload.category);
    toast(loaded && !visible ? '已保存；此记录不在当前筛选范围内' : '记录已保存到本地账本');
  } catch (error) { showError($('#form-error'), error.message); }
  finally { button.disabled = false; button.textContent = '保存记录'; }
}
let confirmResolver = null;
function confirmAction(title, message, label = '确认') {
  $('#confirm-title').textContent = title; $('#confirm-copy').textContent = message; $('#confirm-ok').textContent = label;
  $('#confirm-dialog').showModal(); $('#confirm-cancel').focus();
  return new Promise(resolve => { confirmResolver = resolve; });
}
function finishConfirm(answer) {
  $('#confirm-dialog').close(); const resolve = confirmResolver; confirmResolver = null; resolve?.(answer);
}
async function deleteRecord(row) {
  if (!await confirmAction('删除这笔记录？', `${row.date} · ${row.category} · ${currency(row.amount_cents)}\n删除后无法撤销。需要保留时，可先备份账本。`, '删除记录')) return;
  try { await request(`/api/records/${row.id}`, { method: 'DELETE' }); await refresh(); toast('记录已删除'); }
  catch (error) { showError($('#page-error'), error.message); }
}
async function download(format) {
  try {
    const query = new URLSearchParams(format === 'csv' ? state.filters : {}); query.set('format', format);
    const response = await fetch(`/api/export?${query}`);
    if (!response.ok) { const data = await response.json(); throw new Error(data.error || '导出失败'); }
    const url = URL.createObjectURL(await response.blob());
    const link = element('a'); link.href = url; link.download = `轻记-${format === 'csv' ? '筛选记录' : '完整备份'}-${localDate()}.${format}`;
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 5000);
    toast(format === 'csv' ? '已导出当前筛选记录' : '已导出完整账本备份');
  } catch (error) { showError($('#page-error'), error.message || '导出失败，请检查本地服务'); }
}
async function importFile(event) {
  const file = event.target.files[0]; event.target.value = '';
  if (!file) return;
  try {
    if (file.size > 64 * 1024 * 1024) throw new Error('文件超过 64 MB，请选择较小的 JSON 备份');
    let document;
    try { document = JSON.parse((await file.text()).replace(/^\uFEFF/, '')); }
    catch { throw new Error('文件不是有效的 JSON，请选择轻记导出的备份'); }
    if (!Array.isArray(document?.records)) throw new Error('备份缺少记录列表，请选择轻记格式的文件');
    if (!await confirmAction('导入账本备份', `文件：${file.name}\n包含 ${document.records.length} 笔记录。将合并到当前账本，完全相同的记录自动跳过；冲突或无效数据将取消整次导入。`, '确认导入')) return;
    $('#import-json').disabled = true;
    const result = await request('/api/import', jsonOptions('POST', document));
    await refresh(); toast(`导入完成：新增 ${result.added} 笔，跳过 ${result.skipped} 笔重复记录`);
  } catch (error) { showError($('#page-error'), error.message); }
  finally { $('#import-json').disabled = false; }
}
function markPeriod(value) {
  $$('[data-period]').forEach(button => { const selected = button.dataset.period === value; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', selected); });
}
function setPeriod(period) {
  const now = new Date(); const year = now.getFullYear(); const month = now.getMonth();
  let start = '', end = '';
  if (period === 'month') { start = localDate(new Date(year, month, 1)); end = localDate(new Date(year, month + 1, 0)); }
  if (period === 'last') { start = localDate(new Date(year, month - 1, 1)); end = localDate(new Date(year, month, 0)); }
  if (period === 'year') { start = `${year}-01-01`; end = `${year}-12-31`; }
  $('#filter-start').value = start; $('#filter-end').value = end; markPeriod(period); state.page = 1; refresh(currentFilters());
}
$('#today-label').textContent = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' });
$$('.nav-item').forEach(button => button.addEventListener('click', () => changeView(button.dataset.view)));
$$('[data-period]').forEach(button => button.addEventListener('click', () => setPeriod(button.dataset.period)));
['#filter-start', '#filter-end'].forEach(selector => $(selector).addEventListener('input', () => markPeriod('custom')));
$('#filter-form').addEventListener('submit', event => { event.preventDefault(); state.page = 1; refresh(currentFilters()); });
$('#reset-filters').addEventListener('click', () => { $('#filter-form').reset(); markPeriod('all'); state.page = 1; refresh({}); });
$('#add-record').addEventListener('click', () => openRecord());
$('#empty-add').addEventListener('click', () => openRecord());
$('#close-dialog').addEventListener('click', () => $('#record-dialog').close());
$('#record-form').addEventListener('submit', saveRecord);
$$('#record-form input[name="type"]').forEach(input => input.addEventListener('change', () => { $('#record-category').value = updateCategorySuggestions(input.value); }));
$('#confirm-cancel').addEventListener('click', () => finishConfirm(false));
$('#confirm-ok').addEventListener('click', () => finishConfirm(true));
$('#confirm-dialog').addEventListener('cancel', event => { event.preventDefault(); finishConfirm(false); });
$('#view-all').addEventListener('click', () => changeView('records'));
$('#prev-page').addEventListener('click', () => { state.page--; renderRecords(); });
$('#next-page').addEventListener('click', () => { state.page++; renderRecords(); });
$('#backup-json').addEventListener('click', () => download('json'));
$('#export-csv').addEventListener('click', () => download('csv'));
$('#import-json').addEventListener('click', () => $('#import-file').click());
$('#import-file').addEventListener('change', importFile);
document.addEventListener('visibilitychange', () => { if (!document.hidden && !$('#record-dialog').open && !$('#confirm-dialog').open) refresh(); });
$('#theme-toggle').addEventListener('click', () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
initTheme();
changeView('overview');
refresh({});
