import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const cwd = "/Users/haixintan/Documents/Codex/2026-06-24/2-years-financials";
const outDir = path.join(cwd, "Week2", "outputs", "financials_2026_06_24");
const workDir = path.join(cwd, "Week2", "work");
const tickers = ["COST", "KO", "DELL", "ORCL", "PNC", "WMT", "INTU", "AMZN", "T", "KHC"];
const asOfDate = "2026-06-24";

const fieldDefs = [
  ["totalDebt", "Total Debt ($mm)", ["DebtLongtermAndShorttermCombinedAmount", "LongTermDebtAndFinanceLeaseObligationsCurrentAndNoncurrent", "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", "DebtAndCapitalLeaseObligations", "LongTermDebt"]],
  ["totalLiabilities", "Total Liabilities ($mm)", ["Liabilities"]],
  ["currentDebt", "Short-term / Current Debt ($mm)", ["DebtCurrent", "ShortTermBorrowings", "ShortTermDebt", "LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"]],
  ["currentLiabilities", "Short-term / Current Liabilities ($mm)", ["LiabilitiesCurrent"]],
  ["longTermDebt", "Long-term Debt ($mm)", ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"]],
  ["longTermLiabilities", "Long-term Liabilities ($mm)", ["LiabilitiesNoncurrent"]],
  ["dividendCash", "Dividend Cash Paid ($mm)", ["DividendsCommonStockCash", "PaymentsOfDividendsCommonStock", "PaymentsOfDividends", "DividendsCash", "DividendsCommonStock", "Dividends"]],
  ["dividendPerShare", "Dividend Per Share ($)", ["CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"]],
];

function csvParse(text) {
  const rows = [];
  let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i], n = text[i + 1];
    if (q) {
      if (c === '"' && n === '"') { cell += '"'; i++; }
      else if (c === '"') q = false;
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
    else if (c !== "\r") cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(x => x !== ""));
}

function secUrl(cik) {
  return `https://data.sec.gov/api/xbrl/companyfacts/CIK${cik}.json`;
}

function factUnits(facts, tag) {
  const item = facts?.["us-gaap"]?.[tag] || facts?.dei?.[tag];
  if (!item?.units) return [];
  const preferred = ["USD", "shares", "USD/shares", "pure"];
  for (const u of preferred) if (item.units[u]) return item.units[u].map(x => ({...x, unit: u}));
  const first = Object.keys(item.units)[0];
  return first ? item.units[first].map(x => ({...x, unit: first})) : [];
}

function annualFacts(facts, tag) {
  return factUnits(facts, tag)
    .filter(x => x.form && /^10-K/.test(x.form) && x.fy && (!x.fp || x.fp === "FY") && x.val != null)
    .sort((a, b) => (b.fy - a.fy) || String(b.filed || "").localeCompare(String(a.filed || "")));
}

function latestAnnual(facts, tag, fy) {
  const arr = annualFacts(facts, tag).filter(x => x.fy === fy);
  if (!arr.length) return null;
  arr.sort((a, b) => String(b.filed || "").localeCompare(String(a.filed || "")));
  return arr[0];
}

function latestAny(facts, tag) {
  const arr = factUnits(facts, tag)
    .filter(x => x.val != null && x.end)
    .sort((a, b) => String(b.end).localeCompare(String(a.end)) || String(b.filed || "").localeCompare(String(a.filed || "")));
  return arr[0] || null;
}

function getAnnualYears(facts) {
  const years = new Set();
  for (const tag of ["Liabilities", "Assets", "LongTermDebt", "LiabilitiesCurrent"]) {
    for (const x of annualFacts(facts, tag)) years.add(x.fy);
  }
  return [...years].sort((a, b) => b - a).slice(0, 2).sort((a, b) => a - b);
}

function pickAnnual(facts, candidates, fy) {
  for (const tag of candidates) {
    const f = latestAnnual(facts, tag, fy);
    if (f) return { val: f.val, tag, end: f.end, fy: f.fy, filed: f.filed, form: f.form, unit: f.unit };
  }
  return null;
}

function valueMm(f) {
  if (!f || f.val == null) return null;
  return Math.abs(Number(f.val)) / 1e6;
}

function latestPrice(ticker) {
  const chart = JSON.parse(fsSyncRead(path.join(workDir, "yahoo", `${ticker}_chart.json`)));
  const result = chart.chart?.result?.[0];
  const ts = result?.timestamp || [];
  const quote = result?.indicators?.quote?.[0] || {};
  const adj = result?.indicators?.adjclose?.[0]?.adjclose || [];
  const rows = ts.map((t, i) => {
    const close = quote.close?.[i];
    const adjClose = adj[i];
    if (!Number.isFinite(close)) return null;
    return [new Date(t * 1000).toISOString().slice(0, 10), Number(close), Number.isFinite(adjClose) ? Number(adjClose) : null];
  }).filter(Boolean);
  const last = rows[rows.length - 1];
  return last ? {
    date: last[0],
    close: last[1],
    adjClose: last[2],
    adjFactor: last[2] && last[1] ? last[2] / last[1] : null,
    rows
  } : { date: null, close: null, adjClose: null, adjFactor: null, rows: [] };
}

function fsSyncRead(p) {
  return globalThis.__syncReadFile(p);
}

function parseRate(file, colName) {
  const rows = csvParse(fsSyncRead(path.join(workDir, "fred", file)));
  const header = rows.shift();
  const ixDate = header.indexOf("observation_date");
  const ixVal = header.indexOf(colName);
  return rows.map(r => [r[ixDate], r[ixVal] === "." || r[ixVal] === "" ? null : Number(r[ixVal]) / 100]).filter(r => r[0]);
}

function addComments(sheet, comments) {
  for (const c of comments) {
    try {
      sheet.getRange(c.cell).comment = c.text;
    } catch {}
  }
}

globalThis.__syncReadFile = (p) => {
  throw new Error(`sync reader not initialized: ${p}`);
};

const { readFileSync } = await import("node:fs");
globalThis.__syncReadFile = (p) => readFileSync(p, "utf8");

const companies = [];
const companyRows = [];
const sourceRows = [["Source ID", "Ticker", "Item", "Period / As-of", "Tag / Dataset", "Source URL", "Notes"]];
const comments = [];
let sourceId = 1;

function dellSharesFallback() {
  try {
    const h = fsSyncRead(path.join(workDir, "sec", "DELL_latest_10q.htm"));
    const re = /<ix:nonFraction[^>]*name="dei:EntityCommonStockSharesOutstanding"[^>]*>(.*?)<\/ix:nonFraction>/g;
    let m, total = 0, count = 0;
    while ((m = re.exec(h))) {
      total += Number(m[1].replace(/,/g, ""));
      count++;
    }
    return count ? { val: total, end: "2026-06-02", form: "10-Q", filed: "2026-06-09", source: "DELL 10-Q cover page share classes summed" } : null;
  } catch {
    return null;
  }
}

for (const ticker of tickers) {
  const sec = JSON.parse(await fs.readFile(path.join(workDir, "sec", `${ticker}.json`), "utf8"));
  const cik = String(sec.cik).padStart(10, "0");
  const price = latestPrice(ticker);
  let sharesFact = latestAny(sec.facts, "EntityCommonStockSharesOutstanding");
  if (!sharesFact && ticker === "DELL") sharesFact = dellSharesFallback();
  const shares = sharesFact ? Number(sharesFact.val) : null;
  const marketCap = shares && price.close ? shares * price.close / 1e6 : null;
  companies.push([ticker, sec.entityName || ticker, cik, price.date, price.close, price.adjFactor, shares ? shares / 1e6 : null, marketCap]);
  sourceRows.push([`S${sourceId++}`, ticker, "Latest close / dividend adjustment", price.date, "Yahoo Finance chart API", `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?range=2y&interval=1d&events=history%7Cdiv%7Csplit`, "Dividend adjustment factor computed as adjusted close / close. Market cap computed as latest close x SEC latest shares outstanding."]);
  if (sharesFact) {
    const source = ticker === "DELL" && sharesFact.source
      ? "https://www.sec.gov/Archives/edgar/data/1571996/000157199626000030/dell-20260501.htm"
      : secUrl(cik);
    sourceRows.push([`S${sourceId++}`, ticker, "Shares outstanding", sharesFact.end, "dei:EntityCommonStockSharesOutstanding", source, sharesFact.source || `Filed ${sharesFact.filed || ""}; form ${sharesFact.form || ""}`]);
  }

  const years = getAnnualYears(sec.facts);
  for (const fy of years) {
    const row = { ticker, company: sec.entityName || ticker, cik, fy };
    const picked = {};
    for (const [key, label, tags] of fieldDefs) {
      let f = pickAnnual(sec.facts, tags, fy);
      picked[key] = f;
      row[key] = key === "dividendPerShare" ? (f ? Math.abs(Number(f.val)) : null) : valueMm(f);
      if (f) {
        sourceRows.push([`S${sourceId++}`, ticker, label, `FY ${fy}; end ${f.end}`, `us-gaap:${f.tag}`, secUrl(cik), `Filed ${f.filed || ""}; form ${f.form || ""}; units ${f.unit}`]);
      }
    }
    if (row.longTermLiabilities == null && row.totalLiabilities != null && row.currentLiabilities != null) {
      row.longTermLiabilities = row.totalLiabilities - row.currentLiabilities;
      picked.longTermLiabilities = { tag: "Computed: Liabilities - LiabilitiesCurrent", end: picked.totalLiabilities?.end || picked.currentLiabilities?.end };
      sourceRows.push([`S${sourceId++}`, ticker, "Long-term Liabilities ($mm)", `FY ${fy}`, "Computed", secUrl(cik), "Computed from total liabilities less current liabilities where noncurrent liabilities tag was not available."]);
    }
    companyRows.push([
      ticker, row.company, row.cik, fy,
      row.totalDebt, row.totalLiabilities, row.currentDebt, row.currentLiabilities,
      row.longTermDebt, row.longTermLiabilities, row.dividendCash, row.dividendPerShare,
      price.date, price.close, price.adjFactor, shares ? shares / 1e6 : null, marketCap,
      picked.totalDebt?.tag || "", picked.totalLiabilities?.tag || "", picked.currentDebt?.tag || "",
      picked.currentLiabilities?.tag || "", picked.longTermDebt?.tag || "", picked.longTermLiabilities?.tag || "",
      picked.dividendCash?.tag || "", picked.dividendPerShare?.tag || ""
    ]);
  }
}

const ratesDgs1 = parseRate("DGS1.csv", "DGS1");
const ratesSofr = parseRate("SOFR.csv", "SOFR");
const rateMap = new Map();
for (const [d, v] of ratesDgs1) rateMap.set(d, { date: d, dgs1: v, sofr: null });
for (const [d, v] of ratesSofr) rateMap.set(d, { ...(rateMap.get(d) || { date: d, dgs1: null }), sofr: v });
const ratesRows = [...rateMap.values()].sort((a, b) => a.date.localeCompare(b.date)).map(r => [r.date, r.dgs1, r.sofr]);
const latestDgs1 = [...ratesDgs1].reverse().find(r => r[1] != null);
const latestSofr = [...ratesSofr].reverse().find(r => r[1] != null);
sourceRows.push([`S${sourceId++}`, "Rates", "One-year Treasury rate", latestDgs1?.[0] || "", "FRED DGS1", "https://fred.stlouisfed.org/series/DGS1", "Daily Treasury par yield, percent converted to decimal."]);
sourceRows.push([`S${sourceId++}`, "Rates", "Secured Overnight Financing Rate (SOFR)", latestSofr?.[0] || "", "FRED SOFR", "https://fred.stlouisfed.org/series/SOFR", "Daily SOFR, percent converted to decimal."]);

const wb = Workbook.create();
wb.comments.setSelf({ displayName: "User" });
const cover = wb.worksheets.add("Cover");
const summary = wb.worksheets.add("Summary");
const fin = wb.worksheets.add("Company Financials");
const rates = wb.worksheets.add("Rates");
const prices = wb.worksheets.add("Prices");
const sources = wb.worksheets.add("Sources Audit");
const checks = wb.worksheets.add("Checks");

for (const s of [cover, summary, fin, rates, prices, sources, checks]) s.showGridLines = false;

cover.getRange("A1:H1").merge();
cover.getRange("A1").values = [["Two-Year Financials - Selected Companies"]];
cover.getRange("A3:B9").values = [
  ["Prepared as of", asOfDate],
  ["Companies", tickers.join(", ")],
  ["Financial periods", "Two latest SEC annual fiscal years per company"],
  ["Rates", "Daily DGS1 and SOFR from FRED, 2024-06-24 to 2026-06-24"],
  ["Prices", "Daily closes from Stooq, 2024-06-24 to 2026-06-24"],
  ["Market cap method", "Latest close x latest SEC shares outstanding"],
  ["Workbook notes", "Source tags and URLs are preserved in Company Financials and Sources Audit"],
];
cover.getRange("A11:D15").values = [
  ["Legend", "", "", ""],
  ["Blue font", "Editable/user inputs", "", ""],
  ["Green font", "Linked/reference outputs", "", ""],
  ["Black font", "Imported source data/calculations", "", ""],
  ["Yellow fill", "Key source/method notes", "", ""],
];

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Latest Market Snapshot"]];
summary.getRange("A3:H3").values = [["Ticker", "Company", "CIK", "Latest Close Date", "Closing Price", "Dividend Adj. Factor", "Shares Out. (mm)", "Market Cap ($mm)"]];
summary.getRange(`A4:H${3 + companies.length}`).values = companies;
summary.getRange("I3:J6").values = [
  ["Reference Rate", "Latest"],
  [`1Y Treasury (${latestDgs1?.[0] || "n/a"})`, latestDgs1?.[1] ?? null],
  [`SOFR (${latestSofr?.[0] || "n/a"})`, latestSofr?.[1] ?? null],
  ["Market Cap Method", "Close x SEC shares"],
];

const finHeader = ["Ticker", "Company", "CIK", "Fiscal Year", ...fieldDefs.map(x => x[1]), "Close Date", "Closing Price", "Dividend Adj. Factor", "Shares Out. (mm)", "Market Cap ($mm)", "Total Debt Tag", "Total Liab Tag", "Current Debt Tag", "Current Liab Tag", "LT Debt Tag", "LT Liab Tag", "Dividend Cash Tag", "Dividend/Share Tag"];
fin.getRange(`A1:Y1`).values = [finHeader];
fin.getRange(`A2:Y${1 + companyRows.length}`).values = companyRows;

rates.getRange("A1:C1").values = [["Date", "One-Year Treasury Rate", "SOFR"]];
rates.getRange(`A2:C${1 + ratesRows.length}`).values = ratesRows;

const priceHeader = ["Date", ...tickers];
const priceMap = new Map();
for (const ticker of tickers) {
  for (const [d, close] of latestPrice(ticker).rows) {
    if (!priceMap.has(d)) priceMap.set(d, { Date: d });
    priceMap.get(d)[ticker] = close;
  }
}
const priceRows = [...priceMap.values()].sort((a, b) => a.Date.localeCompare(b.Date)).map(r => [r.Date, ...tickers.map(t => r[t] ?? null)]);
prices.getRange(`A1:K1`).values = [priceHeader];
prices.getRange(`A2:K${1 + priceRows.length}`).values = priceRows;

sources.getRange(`A1:G1`).values = [sourceRows[0]];
sources.getRange(`A2:G${sourceRows.length}`).values = sourceRows.slice(1);

checks.getRange("A1:F1").values = [["Check", "Actual", "Expected", "Difference", "Tolerance", "Status"]];
checks.getRange("A2:F6").values = [
  ["Company row count", companyRows.length, 20, companyRows.length - 20, 0, companyRows.length === 20 ? "OK" : "Review"],
  ["Companies count", companies.length, 10, companies.length - 10, 0, companies.length === 10 ? "OK" : "Review"],
  ["Rates observations", ratesRows.length, "> 400", ratesRows.length > 400 ? 0 : ratesRows.length - 400, 0, ratesRows.length > 400 ? "OK" : "Review"],
  ["Price observations", priceRows.length, "> 400", priceRows.length > 400 ? 0 : priceRows.length - 400, 0, priceRows.length > 400 ? "OK" : "Review"],
  ["Missing key market caps", companies.filter(r => r[6] == null).length, 0, companies.filter(r => r[6] == null).length, 0, companies.every(r => r[6] != null) ? "OK" : "Review"],
];

function styleSheet(sheet, usedRange, headerRange) {
  sheet.getRange(usedRange).format.font.name = "Aptos";
  sheet.getRange(usedRange).format.font.size = 10;
  sheet.getRange(headerRange).format.fill.color = "#1F4E78";
  sheet.getRange(headerRange).format.font.color = "#FFFFFF";
  sheet.getRange(headerRange).format.font.bold = true;
  sheet.getRange(usedRange).format.borders = { preset: "outside", style: "thin", color: "#BFBFBF" };
  sheet.getRange(usedRange).format.autofitColumns();
  sheet.freezePanes.freezeRows(1);
}

cover.getRange("A1:H1").format.fill.color = "#1F4E78";
cover.getRange("A1").format.font.color = "#FFFFFF";
cover.getRange("A1").format.font.bold = true;
cover.getRange("A1").format.font.size = 16;
cover.getRange("A3:B9").format.borders = { preset: "outside", style: "thin", color: "#BFBFBF" };
cover.getRange("A11:D15").format.borders = { preset: "outside", style: "thin", color: "#BFBFBF" };
cover.getRange("A11:D11").format.fill.color = "#FFF2CC";
cover.getRange("A3:A9").format.font.bold = true;
cover.getRange("A:B").format.autofitColumns();

styleSheet(summary, "A3:H13", "A3:H3");
summary.getRange("A1:G1").format.fill.color = "#1F4E78";
summary.getRange("A1").format.font.color = "#FFFFFF";
summary.getRange("A1").format.font.bold = true;
summary.getRange("A1").format.font.size = 14;
summary.getRange("E4:E13").format.numberFormat = "$0.00";
summary.getRange("F4:F13").format.numberFormat = "0.0000x";
summary.getRange("G4:G13").format.numberFormat = "#,##0.0";
summary.getRange("H4:H13").format.numberFormat = "$#,##0";
summary.getRange("J4:J5").format.numberFormat = [["0.00%"], ["0.00%"]];
summary.getRange("I3:J6").format.borders = { preset: "outside", style: "thin", color: "#BFBFBF" };
summary.getRange("I3:J3").format.fill.color = "#1F4E78";
summary.getRange("I3:J3").format.font.color = "#FFFFFF";
summary.getRange("I3:J3").format.font.bold = true;
summary.getRange("B:B").format.columnWidth = 28;
summary.getRange("D:D").format.columnWidth = 15;
summary.getRange("F:F").format.columnWidth = 18;
summary.getRange("I:J").format.columnWidth = 22;

styleSheet(fin, `A1:Y${1 + companyRows.length}`, "A1:Y1");
fin.getRange(`E2:K${1 + companyRows.length}`).format.numberFormat = "$#,##0;[Red]($#,##0);-";
fin.getRange(`L2:L${1 + companyRows.length}`).format.numberFormat = "$0.00;[Red]($0.00);-";
fin.getRange(`N2:N${1 + companyRows.length}`).format.numberFormat = "$0.00;[Red]($0.00);-";
fin.getRange(`O2:O${1 + companyRows.length}`).format.numberFormat = "0.0000x";
fin.getRange(`P2:P${1 + companyRows.length}`).format.numberFormat = "#,##0.0;[Red](#,##0.0);-";
fin.getRange(`Q2:Q${1 + companyRows.length}`).format.numberFormat = "$#,##0;[Red]($#,##0);-";
fin.freezePanes.freezeRows(1);

styleSheet(rates, `A1:C${1 + ratesRows.length}`, "A1:C1");
rates.getRange(`B2:C${1 + ratesRows.length}`).format.numberFormat = "0.00%";
styleSheet(prices, `A1:K${1 + priceRows.length}`, "A1:K1");
prices.getRange(`B2:K${1 + priceRows.length}`).format.numberFormat = "$0.00";
styleSheet(sources, `A1:G${sourceRows.length}`, "A1:G1");
sources.getRange(`F2:G${sourceRows.length}`).format.wrapText = true;
styleSheet(checks, "A1:F6", "A1:F1");
checks.getRange("F2:F6").conditionalFormats.add("containsText", { text: "OK", format: { fill: { color: "#C6EFCE" }, font: { color: "#FFFFFF" }}});
checks.getRange("F2:F6").conditionalFormats.add("containsText", { text: "Review", format: { fill: { color: "#FFC7CE" }, font: { color: "#9C0006" }}});
checks.getRange("A:A").format.columnWidth = 24;
checks.getRange("B:F").format.columnWidth = 13;

for (const s of [summary, fin, rates, prices, sources, checks]) {
  s.getUsedRange().format.wrapText = false;
}
sources.getRange(`F2:G${sourceRows.length}`).format.wrapText = true;
sources.getRange("F:G").format.columnWidth = 55;
fin.getRange("R:Y").format.columnWidth = 24;
prices.getRange("A:K").format.columnWidth = 12;
rates.getRange("A:C").format.columnWidth = 18;

const inspections = [];
inspections.push((await wb.inspect({ kind: "table", sheetId: "Summary", range: "A1:J13", include: "values,formulas", tableMaxRows: 15, tableMaxCols: 10 })).ndjson);
inspections.push((await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "formula error scan" })).ndjson);
await fs.writeFile(path.join(workDir, "verification_inspect.ndjson"), inspections.join("\n"));

for (const [name, range] of [["Summary", "A1:J13"], ["Company Financials", "A1:Y21"], ["Rates", "A1:C25"], ["Prices", "A1:K25"], ["Sources Audit", "A1:G25"], ["Checks", "A1:F6"]]) {
  const blob = await wb.render({ sheetName: name, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(outDir, `${name.replaceAll(" ", "_")}_preview.png`), new Uint8Array(await blob.arrayBuffer()));
}

await fs.mkdir(outDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(outDir, "two_year_financials.xlsx"));
