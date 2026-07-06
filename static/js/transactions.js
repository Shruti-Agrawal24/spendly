/* ===================================================================
   transactions.js — Spendly Transactions Page
   All filtering, sorting, pagination, summary stats, pie chart,
   and bar chart live here. Uses only Vanilla JS, no libraries.

   Transaction data comes from the same DB source the Dashboard uses.
   The server injects the rows as a JSON <script> tag in transactions.html
   (id="tx-data"); this file reads it once at init and feeds the rest
   of the page from there.
   =================================================================== */

"use strict";

/* ------------------------------------------------------------------ */
/* Data source — populated from the #tx-data JSON in transactions.html */
/* ------------------------------------------------------------------ */

const TRANSACTIONS = (() => {
  const node = document.getElementById("tx-data");
  if (!node) return [];
  try {
    const parsed = JSON.parse(node.textContent || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    console.error("Failed to parse transaction data:", e);
    return [];
  }
})();

/* ------------------------------------------------------------------ */
/* Category colour palette — mirrors dashboard.css tokens              */
/* ------------------------------------------------------------------ */

const CATEGORY_COLORS = {
  Food:          { fill: "#1a472a", bg: "#e8f0eb", text: "#1a472a" },
  Transport:     { fill: "#3b82f6", bg: "#dbeafe", text: "#1d4ed8" },
  Bills:         { fill: "#f59e0b", bg: "#fef3c7", text: "#92400e" },
  Health:        { fill: "#ec4899", bg: "#fce7f3", text: "#9d174d" },
  Entertainment: { fill: "#8b5cf6", bg: "#ede9fe", text: "#6d28d9" },
  Shopping:      { fill: "#f97316", bg: "#ffedd5", text: "#c2410c" },
  Other:         { fill: "#a0a0a0", bg: "#eeebe4", text: "#6b6b6b" },
};

// Income source palette — used by the Income Analytics section. Sources are
// freeform text the user types, so we keep a small palette and fall back to
// the warm accent for any source name that isn't pre-listed.
const INCOME_SOURCE_COLORS = {
  Salary:     { fill: "#c17f24", bg: "#fdf3e3", text: "#92580f" },
  Freelance:  { fill: "#1a472a", bg: "#e8f0eb", text: "#1a472a" },
  Bonus:      { fill: "#8b5cf6", bg: "#ede9fe", text: "#6d28d9" },
  Investment: { fill: "#3b82f6", bg: "#dbeafe", text: "#1d4ed8" },
};
const INCOME_SOURCE_FALLBACK = { fill: "#c17f24", bg: "#fdf3e3", text: "#92580f" };

const CATEGORY_ICONS = {
  Food:          "🍔",
  Transport:     "🚗",
  Bills:         "📄",
  Health:        "💊",
  Entertainment: "🎬",
  Shopping:      "🛍️",
  Other:         "📦",
};

/* ------------------------------------------------------------------ */
/* State                                                                */
/* ------------------------------------------------------------------ */

const state = {
  filters: {
    dateStart:   "",
    dateEnd:     "",
    month:       "",
    category:    "",
    search:      "",
    tableSearch: "",
  },
  sort: {
    col: "date",
    dir: "desc",   /* "asc" | "desc" */
  },
  page:    1,
  perPage: 10,
};

/* ------------------------------------------------------------------ */
/* DOM refs                                                             */
/* ------------------------------------------------------------------ */

const $ = id => document.getElementById(id);

const els = {
  filterStart:   $("filter-date-start"),
  filterEnd:     $("filter-date-end"),
  filterMonth:   $("filter-month"),
  filterCat:     $("filter-category"),
  filterSearch:  $("filter-search"),
  btnReset:      $("btn-reset-filters"),
  btnEmptyReset: $("btn-empty-reset"),

  summaryExpenses:    $("summary-expenses"),
  summaryExpensesSub: $("summary-expenses-sub"),
  summaryIncome:      $("summary-income"),
  summaryIncomeSub:   $("summary-income-sub"),
  summaryBalance:     $("summary-balance"),
  summaryCount:       $("summary-count"),

  // Analytics — Expense section
  pieChart:      $("tx-pie-chart"),
  catBreakdown:  $("tx-cat-breakdown"),
  lineChart:     $("tx-line-chart"),
  lineTotalSpent: $("line-total-spent"),
  lineTotalSub:   $("line-total-sub"),

  // Analytics — Income section
  pieChartIncome:     $("tx-pie-chart-income"),
  catBreakdownIncome: $("tx-cat-breakdown-income"),
  lineChartIncome:    $("tx-line-chart-income"),
  lineTotalIncome:    $("line-total-income"),
  lineTotalSubIncome: $("line-total-sub-income"),

  tableSearch:   $("table-search"),
  tableCount:    $("table-count"),
  tableBody:     $("tx-table-body"),
  emptyState:    $("tx-empty"),
  pagination:    $("tx-pagination"),
  btnPrev:       $("btn-prev"),
  btnNext:       $("btn-next"),
  pageInfo:      $("pagination-info"),
};

/* ------------------------------------------------------------------ */
/* Formatting helpers                                                   */
/* ------------------------------------------------------------------ */

const fmt = {
  currency: n => "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  date: s => {
    const [y, m, d] = s.split("-");
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return `${d} ${months[+m - 1]} ${y}`;
  },
};

/* ------------------------------------------------------------------ */
/* Filtering                                                            */
/* ------------------------------------------------------------------ */

function applyFilters(transactions) {
  const { dateStart, dateEnd, month, category, search } = state.filters;

  return transactions.filter(tx => {
    if (dateStart && tx.date < dateStart)  return false;
    if (dateEnd   && tx.date > dateEnd)    return false;
    if (month && !tx.date.startsWith(`${new Date().getFullYear()}-${String(month).padStart(2, "0")}`)) {
      // month filter: check month portion of tx date
      const txMonth = tx.date.slice(5, 7);
      if (txMonth !== String(month).padStart(2, "0")) return false;
    }
    if (category && tx.category !== category) return false;
    if (search) {
      const q = search.toLowerCase();
      if (!tx.description.toLowerCase().includes(q) &&
          !tx.category.toLowerCase().includes(q)) return false;
    }
    return true;
  });
}

function applyTableSearch(transactions) {
  const q = state.filters.tableSearch.trim().toLowerCase();
  if (!q) return transactions;
  return transactions.filter(tx =>
    tx.description.toLowerCase().includes(q) ||
    tx.category.toLowerCase().includes(q) ||
    tx.date.includes(q) ||
    tx.type.toLowerCase().includes(q)
  );
}

/* ------------------------------------------------------------------ */
/* Sorting                                                              */
/* ------------------------------------------------------------------ */

function applySorting(transactions) {
  const { col, dir } = state.sort;
  const mult = dir === "asc" ? 1 : -1;

  return [...transactions].sort((a, b) => {
    let va = a[col], vb = b[col];
    if (col === "amount") return (va - vb) * mult;
    va = String(va).toLowerCase();
    vb = String(vb).toLowerCase();
    return va < vb ? -mult : va > vb ? mult : 0;
  });
}

/* ------------------------------------------------------------------ */
/* Summary stats                                                        */
/* ------------------------------------------------------------------ */

function updateSummary(filtered) {
  const expenses = filtered.filter(t => t.type === "expense");
  const income   = filtered.filter(t => t.type === "income");

  const totalExp = expenses.reduce((s, t) => s + t.amount, 0);
  const totalInc = income.reduce((s, t) => s + t.amount, 0);
  const balance  = totalInc - totalExp;

  els.summaryExpenses.textContent    = fmt.currency(totalExp);
  els.summaryExpensesSub.textContent = `${expenses.length} expense transaction${expenses.length !== 1 ? "s" : ""}`;
  els.summaryIncome.textContent      = fmt.currency(totalInc);
  els.summaryIncomeSub.textContent   = `${income.length} income transaction${income.length !== 1 ? "s" : ""}`;

  els.summaryBalance.textContent = fmt.currency(balance);
  els.summaryBalance.className   = "transactions-summary-value" +
    (balance < 0 ? " transactions-summary-value--negative" : "");

  els.summaryCount.textContent = filtered.length;
}

/* ------------------------------------------------------------------ */
/* SVG pie helpers                                                       */
/* ------------------------------------------------------------------ */

function polarToXY(cx, cy, r, deg) {
  const rad = (deg - 90) * (Math.PI / 180);
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function arcPath(cx, cy, r, startDeg, endDeg) {
  const span = endDeg - startDeg;
  if (span >= 359.999) {
    const [x1, y1] = polarToXY(cx, cy, r, 0);
    const [x2, y2] = polarToXY(cx, cy, r, 180);
    return `M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 1 1 ${x2.toFixed(2)} ${y2.toFixed(2)} A ${r} ${r} 0 1 1 ${x1.toFixed(2)} ${y1.toFixed(2)} Z`;
  }
  const large = span > 180 ? 1 : 0;
  const [x1, y1] = polarToXY(cx, cy, r, startDeg);
  const [x2, y2] = polarToXY(cx, cy, r, endDeg);
  return `M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`;
}

/* ------------------------------------------------------------------ */
/* Category card — pie + horizontal progress-bar breakdown              */
/* ------------------------------------------------------------------ */

function updateCategoryCard(filtered) {
  const expenses = filtered.filter(t => t.type === "expense");
  const totalExp = expenses.reduce((s, t) => s + t.amount, 0);

  const catMap = {};
  for (const tx of expenses) catMap[tx.category] = (catMap[tx.category] || 0) + tx.amount;
  const cats = Object.entries(catMap).sort((a, b) => b[1] - a[1]);

  const svgNS = "http://www.w3.org/2000/svg";
  els.pieChart.innerHTML = "";
  els.catBreakdown.innerHTML = "";

  // ── Empty state ──
  if (cats.length === 0) {
    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", 100); circle.setAttribute("cy", 100);
    circle.setAttribute("r",  80);  circle.setAttribute("fill", "#eeebe4");
    els.pieChart.appendChild(circle);

    const li = document.createElement("li");
    li.style.cssText = "color:var(--ink-muted);font-size:0.85rem;padding:1rem 0;";
    li.textContent = "No expense data for selected filters.";
    els.catBreakdown.appendChild(li);
    return;
  }

  // ── Pie slices ──
  let cumDeg = 0;
  for (const [name, amount] of cats) {
    const span  = (amount / totalExp) * 360;
    const color = (CATEGORY_COLORS[name] || CATEGORY_COLORS.Other).fill;
    const path  = document.createElementNS(svgNS, "path");
    path.setAttribute("d", arcPath(100, 100, 80, cumDeg, cumDeg + span));
    path.setAttribute("fill", color);
    const title = document.createElementNS(svgNS, "title");
    title.textContent = `${name} — ${((amount / totalExp) * 100).toFixed(1)}%`;
    path.appendChild(title);
    els.pieChart.appendChild(path);
    cumDeg += span;
  }

  // ── Horizontal progress bars ──
  const maxCatAmt = cats[0][1]; // largest category for scaling bars

  for (const [name, amount] of cats) {
    const pct     = totalExp > 0 ? Math.round((amount / totalExp) * 100) : 0;
    const barPct  = maxCatAmt > 0 ? (amount / maxCatAmt) * 100 : 0;
    const color   = (CATEGORY_COLORS[name] || CATEGORY_COLORS.Other).fill;
    const pctText = pct === 0 ? "0%" : `${pct}%`;

    const li = document.createElement("li");
    li.className = "analytics-breakdown-row";

    li.innerHTML = `
      <span class="analytics-breakdown-dot" style="background:${color};"></span>
      <span class="analytics-breakdown-name">${escapeHtml(name)}</span>
      <div class="analytics-breakdown-track">
        <div class="analytics-breakdown-fill" style="width:${barPct.toFixed(1)}%;background:${color};"></div>
      </div>
      <span class="analytics-breakdown-pct" style="color:${color};">${pctText}</span>
      <span class="analytics-breakdown-amt">${fmt.currency(amount)}</span>
    `;
    els.catBreakdown.appendChild(li);
  }
}

/* ------------------------------------------------------------------ */
/* SVG Area Line Chart — Spending Over Time                             */
/* ------------------------------------------------------------------ */

function updateLineChart(filtered) {
  const expenses = filtered.filter(t => t.type === "expense");
  const totalExp = expenses.reduce((s, t) => s + t.amount, 0);

  // ── Total Spent summary ──
  els.lineTotalSpent.textContent = fmt.currency(totalExp);
  els.lineTotalSub.textContent   = totalExp > 0 ? "All filtered expenses" : "";

  // ── Group by date (YYYY-MM-DD) ──
  const dateMap = {};
  for (const tx of expenses) {
    dateMap[tx.date] = (dateMap[tx.date] || 0) + tx.amount;
  }
  const dates  = Object.keys(dateMap).sort();
  const values = dates.map(d => dateMap[d]);

  const svgEl = els.lineChart;
  svgEl.innerHTML = "";
  const svgNS = "http://www.w3.org/2000/svg";

  if (dates.length === 0) {
    const t = document.createElementNS(svgNS, "text");
    t.setAttribute("x", "50%"); t.setAttribute("y", "50%");
    t.setAttribute("text-anchor", "middle"); t.setAttribute("dominant-baseline", "middle");
    t.setAttribute("fill", "#a0a0a0"); t.setAttribute("font-size", "13");
    t.textContent = "No expense data for the selected filters.";
    svgEl.appendChild(t);
    return;
  }

  // ── Layout constants ──
  const W = 600, H = 200;         // internal SVG coordinate space
  const PAD = { top: 16, right: 20, bottom: 36, left: 52 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top  - PAD.bottom;
  svgEl.setAttribute("viewBox", `0 0 ${W} ${H}`);

  const maxV  = Math.max(...values);
  const niceMax = niceRound(maxV * 1.15);  // 15% headroom
  const Y_TICKS = 4;

  // coordinate helpers
  const xPos = i => PAD.left + (dates.length === 1 ? chartW / 2 : (i / (dates.length - 1)) * chartW);
  const yPos = v => PAD.top  + chartH - (v / niceMax) * chartH;

  // ── Y-axis grid lines + labels ──
  for (let t = 0; t <= Y_TICKS; t++) {
    const val = (niceMax / Y_TICKS) * t;
    const y   = yPos(val);

    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("x1", PAD.left); line.setAttribute("x2", W - PAD.right);
    line.setAttribute("y1", y);        line.setAttribute("y2", y);
    line.setAttribute("stroke", t === 0 ? "#d0ccc6" : "#eeebe4");
    line.setAttribute("stroke-width", t === 0 ? "1.5" : "1");
    svgEl.appendChild(line);

    if (t > 0) {
      const lbl = document.createElementNS(svgNS, "text");
      lbl.setAttribute("x", PAD.left - 6);
      lbl.setAttribute("y", y + 4);
      lbl.setAttribute("text-anchor", "end");
      lbl.setAttribute("font-size", "10");
      lbl.setAttribute("fill", "#a0a0a0");
      lbl.textContent = fmtYLabel(val);
      svgEl.appendChild(lbl);
    }
  }

  // ── X-axis date labels (show ~5 evenly spaced) ──
  const xLabelCount = Math.min(dates.length, 5);
  for (let i = 0; i < xLabelCount; i++) {
    const idx  = Math.round((i / (xLabelCount - 1 || 1)) * (dates.length - 1));
    const x    = xPos(idx);
    const lbl  = document.createElementNS(svgNS, "text");
    lbl.setAttribute("x", x);
    lbl.setAttribute("y", H - PAD.bottom + 14);
    lbl.setAttribute("text-anchor", "middle");
    lbl.setAttribute("font-size", "10");
    lbl.setAttribute("fill", "#a0a0a0");
    lbl.textContent = shortDate(dates[idx]);
    svgEl.appendChild(lbl);
  }

  // ── Build point coordinates ──
  const pts = dates.map((d, i) => [xPos(i), yPos(values[i])]);

  // ── Filled area (gradient) ──
  const gradId = "line-area-grad";
  const defs   = document.createElementNS(svgNS, "defs");
  const grad   = document.createElementNS(svgNS, "linearGradient");
  grad.setAttribute("id", gradId);
  grad.setAttribute("x1", "0"); grad.setAttribute("y1", "0");
  grad.setAttribute("x2", "0"); grad.setAttribute("y2", "1");
  const stop1 = document.createElementNS(svgNS, "stop");
  stop1.setAttribute("offset", "0%");   stop1.setAttribute("stop-color", "#1a472a"); stop1.setAttribute("stop-opacity", "0.18");
  const stop2 = document.createElementNS(svgNS, "stop");
  stop2.setAttribute("offset", "100%"); stop2.setAttribute("stop-color", "#1a472a"); stop2.setAttribute("stop-opacity", "0");
  grad.append(stop1, stop2);
  defs.appendChild(grad);
  svgEl.appendChild(defs);

  const baseY = yPos(0);
  const areaD = [
    `M ${pts[0][0]} ${baseY}`,
    ...pts.map(([x, y]) => `L ${x.toFixed(1)} ${y.toFixed(1)}`),
    `L ${pts[pts.length-1][0]} ${baseY}`,
    "Z"
  ].join(" ");

  const area = document.createElementNS(svgNS, "path");
  area.setAttribute("d", areaD);
  area.setAttribute("fill", `url(#${gradId})`);
  svgEl.appendChild(area);

  // ── Line ──
  const lineD = pts.map(([x,y], i) => `${i===0?"M":"L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const linePath = document.createElementNS(svgNS, "path");
  linePath.setAttribute("d", lineD);
  linePath.setAttribute("fill", "none");
  linePath.setAttribute("stroke", "#1a472a");
  linePath.setAttribute("stroke-width", "2");
  linePath.setAttribute("stroke-linejoin", "round");
  linePath.setAttribute("stroke-linecap",  "round");
  svgEl.appendChild(linePath);

  // ── Dot markers ──
  for (const [x, y] of pts) {
    const outer = document.createElementNS(svgNS, "circle");
    outer.setAttribute("cx", x.toFixed(1)); outer.setAttribute("cy", y.toFixed(1));
    outer.setAttribute("r", "4"); outer.setAttribute("fill", "#ffffff");
    outer.setAttribute("stroke", "#1a472a"); outer.setAttribute("stroke-width", "2");
    svgEl.appendChild(outer);
  }
}

/* ------------------------------------------------------------------ */
/* Income Analytics — mirrors updateCategoryCard/updateLineChart but    */
/* operates on income-typed rows and writes to the income DOM nodes.    */
/* ------------------------------------------------------------------ */

function updateIncomeCategoryCard(filtered) {
  const incomes = filtered.filter(t => t.type === "income");
  const totalInc = incomes.reduce((s, t) => s + t.amount, 0);

  const srcMap = {};
  for (const tx of incomes) srcMap[tx.category] = (srcMap[tx.category] || 0) + tx.amount;
  const sources = Object.entries(srcMap).sort((a, b) => b[1] - a[1]);

  const svgNS = "http://www.w3.org/2000/svg";
  els.pieChartIncome.innerHTML = "";
  els.catBreakdownIncome.innerHTML = "";

  // ── Empty state ──
  if (sources.length === 0) {
    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", 100); circle.setAttribute("cy", 100);
    circle.setAttribute("r",  80);  circle.setAttribute("fill", "#eeebe4");
    els.pieChartIncome.appendChild(circle);

    const li = document.createElement("li");
    li.style.cssText = "color:var(--ink-muted);font-size:0.85rem;padding:1rem 0;";
    li.textContent = "No income data for selected filters.";
    els.catBreakdownIncome.appendChild(li);
    return;
  }

  // ── Pie slices ──
  let cumDeg = 0;
  for (const [name, amount] of sources) {
    const span  = (amount / totalInc) * 360;
    const color = (INCOME_SOURCE_COLORS[name] || INCOME_SOURCE_FALLBACK).fill;
    const path  = document.createElementNS(svgNS, "path");
    path.setAttribute("d", arcPath(100, 100, 80, cumDeg, cumDeg + span));
    path.setAttribute("fill", color);
    const title = document.createElementNS(svgNS, "title");
    title.textContent = `${name} — ${((amount / totalInc) * 100).toFixed(1)}%`;
    path.appendChild(title);
    els.pieChartIncome.appendChild(path);
    cumDeg += span;
  }

  // ── Horizontal progress bars ──
  const maxSrcAmt = sources[0][1]; // largest source for scaling bars

  for (const [name, amount] of sources) {
    const pct     = totalInc > 0 ? Math.round((amount / totalInc) * 100) : 0;
    const barPct  = maxSrcAmt > 0 ? (amount / maxSrcAmt) * 100 : 0;
    const color   = (INCOME_SOURCE_COLORS[name] || INCOME_SOURCE_FALLBACK).fill;
    const pctText = pct === 0 ? "0%" : `${pct}%`;

    const li = document.createElement("li");
    li.className = "analytics-breakdown-row";

    li.innerHTML = `
      <span class="analytics-breakdown-dot" style="background:${color};"></span>
      <span class="analytics-breakdown-name">${escapeHtml(name)}</span>
      <div class="analytics-breakdown-track">
        <div class="analytics-breakdown-fill" style="width:${barPct.toFixed(1)}%;background:${color};"></div>
      </div>
      <span class="analytics-breakdown-pct" style="color:${color};">${pctText}</span>
      <span class="analytics-breakdown-amt">${fmt.currency(amount)}</span>
    `;
    els.catBreakdownIncome.appendChild(li);
  }
}

function updateIncomeLineChart(filtered) {
  const incomes = filtered.filter(t => t.type === "income");
  const totalInc = incomes.reduce((s, t) => s + t.amount, 0);

  // ── Total Earned summary ──
  els.lineTotalIncome.textContent = fmt.currency(totalInc);
  els.lineTotalSubIncome.textContent = totalInc > 0 ? "All filtered income" : "";

  // ── Group by date (YYYY-MM-DD) ──
  const dateMap = {};
  for (const tx of incomes) {
    dateMap[tx.date] = (dateMap[tx.date] || 0) + tx.amount;
  }
  const dates  = Object.keys(dateMap).sort();
  const values = dates.map(d => dateMap[d]);

  const svgEl = els.lineChartIncome;
  svgEl.innerHTML = "";
  const svgNS = "http://www.w3.org/2000/svg";

  if (dates.length === 0) {
    const t = document.createElementNS(svgNS, "text");
    t.setAttribute("x", "50%"); t.setAttribute("y", "50%");
    t.setAttribute("text-anchor", "middle"); t.setAttribute("dominant-baseline", "middle");
    t.setAttribute("fill", "#a0a0a0"); t.setAttribute("font-size", "13");
    t.textContent = "No income data for the selected filters.";
    svgEl.appendChild(t);
    return;
  }

  // ── Layout constants ──
  const W = 600, H = 200;
  const PAD = { top: 16, right: 20, bottom: 36, left: 52 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top  - PAD.bottom;
  svgEl.setAttribute("viewBox", `0 0 ${W} ${H}`);

  const maxV  = Math.max(...values);
  const niceMax = niceRound(maxV * 1.15);
  const Y_TICKS = 4;

  const xPos = i => PAD.left + (dates.length === 1 ? chartW / 2 : (i / (dates.length - 1)) * chartW);
  const yPos = v => PAD.top  + chartH - (v / niceMax) * chartH;

  // ── Y-axis grid lines + labels ──
  for (let t = 0; t <= Y_TICKS; t++) {
    const val = (niceMax / Y_TICKS) * t;
    const y   = yPos(val);

    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("x1", PAD.left); line.setAttribute("x2", W - PAD.right);
    line.setAttribute("y1", y);        line.setAttribute("y2", y);
    line.setAttribute("stroke", t === 0 ? "#d0ccc6" : "#eeebe4");
    line.setAttribute("stroke-width", t === 0 ? "1.5" : "1");
    svgEl.appendChild(line);

    if (t > 0) {
      const lbl = document.createElementNS(svgNS, "text");
      lbl.setAttribute("x", PAD.left - 6);
      lbl.setAttribute("y", y + 4);
      lbl.setAttribute("text-anchor", "end");
      lbl.setAttribute("font-size", "10");
      lbl.setAttribute("fill", "#a0a0a0");
      lbl.textContent = fmtYLabel(val);
      svgEl.appendChild(lbl);
    }
  }

  // ── X-axis date labels (show ~5 evenly spaced) ──
  const xLabelCount = Math.min(dates.length, 5);
  for (let i = 0; i < xLabelCount; i++) {
    const idx  = Math.round((i / (xLabelCount - 1 || 1)) * (dates.length - 1));
    const x    = xPos(idx);
    const lbl  = document.createElementNS(svgNS, "text");
    lbl.setAttribute("x", x);
    lbl.setAttribute("y", H - PAD.bottom + 14);
    lbl.setAttribute("text-anchor", "middle");
    lbl.setAttribute("font-size", "10");
    lbl.setAttribute("fill", "#a0a0a0");
    lbl.textContent = shortDate(dates[idx]);
    svgEl.appendChild(lbl);
  }

  // ── Build point coordinates ──
  const pts = dates.map((d, i) => [xPos(i), yPos(values[i])]);

  // ── Filled area (gradient) — uses the income accent (--accent-2 = #c17f24) ──
  const gradId = "line-area-grad-income";
  const defs   = document.createElementNS(svgNS, "defs");
  const grad   = document.createElementNS(svgNS, "linearGradient");
  grad.setAttribute("id", gradId);
  grad.setAttribute("x1", "0"); grad.setAttribute("y1", "0");
  grad.setAttribute("x2", "0"); grad.setAttribute("y2", "1");
  const stop1 = document.createElementNS(svgNS, "stop");
  stop1.setAttribute("offset", "0%");   stop1.setAttribute("stop-color", "#c17f24"); stop1.setAttribute("stop-opacity", "0.18");
  const stop2 = document.createElementNS(svgNS, "stop");
  stop2.setAttribute("offset", "100%"); stop2.setAttribute("stop-color", "#c17f24"); stop2.setAttribute("stop-opacity", "0");
  grad.append(stop1, stop2);
  defs.appendChild(grad);
  svgEl.appendChild(defs);

  const baseY = yPos(0);
  const areaD = [
    `M ${pts[0][0]} ${baseY}`,
    ...pts.map(([x, y]) => `L ${x.toFixed(1)} ${y.toFixed(1)}`),
    `L ${pts[pts.length-1][0]} ${baseY}`,
    "Z"
  ].join(" ");

  const area = document.createElementNS(svgNS, "path");
  area.setAttribute("d", areaD);
  area.setAttribute("fill", `url(#${gradId})`);
  svgEl.appendChild(area);

  // ── Line ──
  const lineD = pts.map(([x,y], i) => `${i===0?"M":"L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const linePath = document.createElementNS(svgNS, "path");
  linePath.setAttribute("d", lineD);
  linePath.setAttribute("fill", "none");
  linePath.setAttribute("stroke", "#c17f24");
  linePath.setAttribute("stroke-width", "2");
  linePath.setAttribute("stroke-linejoin", "round");
  linePath.setAttribute("stroke-linecap",  "round");
  svgEl.appendChild(linePath);

  // ── Dot markers ──
  for (const [x, y] of pts) {
    const outer = document.createElementNS(svgNS, "circle");
    outer.setAttribute("cx", x.toFixed(1)); outer.setAttribute("cy", y.toFixed(1));
    outer.setAttribute("r", "4"); outer.setAttribute("fill", "#ffffff");
    outer.setAttribute("stroke", "#c17f24"); outer.setAttribute("stroke-width", "2");
    svgEl.appendChild(outer);
  }
}

/* ---- Helpers for line chart ---- */

function niceRound(v) {
  if (v <= 0) return 1000;
  const exp  = Math.pow(10, Math.floor(Math.log10(v)));
  const frac = v / exp;
  const nice = frac <= 1 ? 1 : frac <= 2 ? 2 : frac <= 5 ? 5 : 10;
  return nice * exp;
}

function fmtYLabel(v) {
  if (v >= 100000) return "₹" + (v / 100000).toFixed(1) + "L";
  if (v >= 1000)   return "₹" + (v / 1000).toFixed(0)   + "K";
  return "₹" + v.toFixed(0);
}

function shortDate(s) {
  const [, m, d] = s.split("-");
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[+m-1]} ${+d}`;
}

/* ------------------------------------------------------------------ */
/* Table rendering & pagination                                         */
/* ------------------------------------------------------------------ */

function renderTable(rows) {
  const total = rows.length;
  const pages = Math.max(1, Math.ceil(total / state.perPage));
  state.page  = Math.min(state.page, pages);

  const start = (state.page - 1) * state.perPage;
  const slice = rows.slice(start, start + state.perPage);

  els.tableBody.innerHTML = "";

  if (slice.length === 0) {
    els.emptyState.hidden    = false;
    els.pagination.hidden    = true;
    els.tableBody.closest("table").style.display = "none";
    els.tableCount.textContent = "Showing 0 of 0";
    return;
  }

  els.emptyState.hidden  = true;
  els.pagination.hidden  = false;
  els.tableBody.closest("table").style.display = "";

  for (const tx of slice) {
    const tr = document.createElement("tr");

    const catColor  = CATEGORY_COLORS[tx.category] || CATEGORY_COLORS.Other;
    const isIncome  = tx.type === "income";
    const typeClass = isIncome ? "transactions-type--income" : "transactions-type--expense";
    const typeLabel = isIncome ? "Income" : "Expense";
    const amtClass  = isIncome ? " transactions-amount--income" : "";

    tr.innerHTML = `
      <td class="profile-table-date">${fmt.date(tx.date)}</td>
      <td class="profile-table-description">${escapeHtml(tx.description)}</td>
      <td>
        <span class="category-badge" style="background:${catColor.bg};color:${catColor.text};">
          ${CATEGORY_ICONS[tx.category] || ""} ${escapeHtml(tx.category)}
        </span>
      </td>
      <td><span class="transactions-type ${typeClass}">${typeLabel}</span></td>
      <td class="profile-table-amount${amtClass}">${fmt.currency(tx.amount)}</td>
    `;
    els.tableBody.appendChild(tr);
  }

  // Update row count
  els.tableCount.textContent = `Showing ${start + 1}–${Math.min(start + state.perPage, total)} of ${total}`;

  // Pagination controls
  els.btnPrev.disabled  = state.page <= 1;
  els.btnNext.disabled  = state.page >= pages;
  els.pageInfo.textContent = `Page ${state.page} of ${pages}`;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ------------------------------------------------------------------ */
/* Sort header indicators                                               */
/* ------------------------------------------------------------------ */

function updateSortHeaders() {
  document.querySelectorAll(".transactions-th").forEach(th => {
    th.classList.remove("transactions-th--sorted-asc", "transactions-th--sorted-desc");
    const ind = th.querySelector(".transactions-sort-ind");
    if (ind) ind.textContent = "↕";
    th.removeAttribute("aria-sort");
  });

  const activeTh = document.querySelector(`[data-col="${state.sort.col}"]`);
  if (activeTh) {
    const cls  = state.sort.dir === "asc" ? "transactions-th--sorted-asc" : "transactions-th--sorted-desc";
    const icon = state.sort.dir === "asc" ? "↑" : "↓";
    activeTh.classList.add(cls);
    const ind = activeTh.querySelector(".transactions-sort-ind");
    if (ind) ind.textContent = icon;
    activeTh.setAttribute("aria-sort", state.sort.dir === "asc" ? "ascending" : "descending");
  }
}

/* ------------------------------------------------------------------ */
/* Master render — called whenever any filter/sort/page changes        */
/* ------------------------------------------------------------------ */

function render() {
  // 1. Apply top-level filters
  const filtered = applyFilters(TRANSACTIONS);

  // 2. Update summary, charts, and stats (always from filter-level data)
  updateSummary(filtered);
  updateCategoryCard(filtered);
  updateLineChart(filtered);
  updateIncomeCategoryCard(filtered);
  updateIncomeLineChart(filtered);

  // 3. Apply inline table search on top of filtered set
  const searched = applyTableSearch(filtered);

  // 4. Sort
  const sorted = applySorting(searched);

  // 5. Paginate and render rows
  renderTable(sorted);

  // 6. Update sort header visual
  updateSortHeaders();
}

/* ------------------------------------------------------------------ */
/* Event wiring                                                         */
/* ------------------------------------------------------------------ */

function resetFilters() {
  els.filterStart.value  = "";
  els.filterEnd.value    = "";
  els.filterMonth.value  = "";
  els.filterCat.value    = "";
  els.filterSearch.value = "";
  els.tableSearch.value  = "";
  state.filters = { dateStart: "", dateEnd: "", month: "", category: "", search: "", tableSearch: "" };
  state.page    = 1;
  render();
}

function bindFilters() {
  els.filterStart.addEventListener("change", e => {
    state.filters.dateStart = e.target.value;
    state.page = 1;
    render();
  });

  els.filterEnd.addEventListener("change", e => {
    state.filters.dateEnd = e.target.value;
    state.page = 1;
    render();
  });

  els.filterMonth.addEventListener("change", e => {
    state.filters.month = e.target.value;
    state.page = 1;
    render();
  });

  els.filterCat.addEventListener("change", e => {
    state.filters.category = e.target.value;
    state.page = 1;
    render();
  });

  els.filterSearch.addEventListener("input", e => {
    state.filters.search = e.target.value.trim();
    state.page = 1;
    render();
  });

  els.tableSearch.addEventListener("input", e => {
    state.filters.tableSearch = e.target.value.trim();
    state.page = 1;
    render();
  });

  els.btnReset.addEventListener("click", resetFilters);
  els.btnEmptyReset && els.btnEmptyReset.addEventListener("click", resetFilters);
}

function bindSortHeaders() {
  document.querySelectorAll(".transactions-th").forEach(th => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      if (state.sort.col === col) {
        state.sort.dir = state.sort.dir === "asc" ? "desc" : "asc";
      } else {
        state.sort.col = col;
        state.sort.dir = col === "amount" ? "desc" : "asc";
      }
      state.page = 1;
      render();
    });
    // Keyboard accessibility
    th.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        th.click();
      }
    });
  });
}

function bindPagination() {
  els.btnPrev.addEventListener("click", () => {
    if (state.page > 1) { state.page--; render(); }
  });

  els.btnNext.addEventListener("click", () => {
    const filtered = applyFilters(TRANSACTIONS);
    const searched = applyTableSearch(filtered);
    const pages    = Math.max(1, Math.ceil(searched.length / state.perPage));
    if (state.page < pages) { state.page++; render(); }
  });
}

/* ------------------------------------------------------------------ */
/* Init                                                                 */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
  bindFilters();
  bindSortHeaders();
  bindPagination();
  render();
});
