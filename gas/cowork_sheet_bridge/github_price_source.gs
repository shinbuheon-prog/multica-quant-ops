// Reference code, not auto-deployed by this repository.
//
// docs/FUNDAMENTALS_INTEGRATION.md Phase 10 ("기존 Cowork 시트가 저장소 산출물을
// 소스로 읽도록 연결") asks the Cowork pipeline's existing CSV-based Google Sheet
// to pick up GitHub Actions' daily Stooq price refresh
// (ops/prices/daily_prices.csv, from Phase 5 -- see
// src/multica_quant_ops/data/refresh_daily_prices.py and
// .github/workflows/refresh-daily-prices.yml) instead of only relying on
// whatever price the Cowork pipeline itself last collected.
//
// This file is NOT wired into the live sheet automatically -- unlike a git
// push, saving Apps Script code takes effect immediately with no review
// step, and this repo has no way to test Apps Script execution. Paste it
// into the *existing* Apps Script project behind the Cowork sheet (the one
// with refreshMetrics()/resolvePrice_() etc. -- see /home/claude/gas/Code.gs
// in that session) as a new, separate function, review it, and call it
// manually (or wire it into onOpen()/refreshPricesAndRevalue()) once you've
// checked it against a real run. It intentionally never overwrites a cell by
// itself -- it only returns a lookup map for the caller to use, following
// the same "error without overwriting existing data" convention as
// refreshMetrics() in the main script.
//
// ---------------------------------------------------------------------------
// Prerequisite decision this repo cannot make for you: is
// shinbuheon-prog/multica-quant-ops public or private?
//   - Public repo: UrlFetchApp can hit raw.githubusercontent.com with no
//     credential.
//   - Private repo: UrlFetchApp needs an Authorization: token <PAT> header.
//     Store the PAT in this Apps Script project's Script Properties
//     (File > Project properties > Script properties) under a key like
//     GITHUB_PAT -- never hard-code it in this file. A fine-grained PAT with
//     read-only "Contents" access to just this repo is enough.
// ---------------------------------------------------------------------------

var GITHUB_PRICE_CSV_CONFIG = {
  // Change 'main' if the workflow commits to a different branch.
  RAW_URL: 'https://raw.githubusercontent.com/shinbuheon-prog/multica-quant-ops/main/ops/prices/daily_prices.csv',
  // Set true only after confirming the repo is private and GITHUB_PAT is set
  // in Script Properties.
  REQUIRES_AUTH: false,
};

/**
 * Fetch and parse ops/prices/daily_prices.csv (columns:
 * ticker,date,open,high,low,close,volume,updated_at,source,stale -- see
 * PriceRow.to_csv_row() in refresh_daily_prices.py) into
 * { TICKER: { close, date, staleFromGithub, updatedAt } }.
 *
 * Returns an empty map (never throws) on any fetch/parse failure, with the
 * failure reason logged via Logger.log -- a GitHub Actions outage or an
 * unpopulated ops/tickers.txt (harmless no-op per Phase 5) should degrade to
 * "no GitHub price data today", not break the existing refresh.
 */
function fetchGithubDailyPrices_() {
  var headers = {};
  if (GITHUB_PRICE_CSV_CONFIG.REQUIRES_AUTH) {
    var pat = PropertiesService.getScriptProperties().getProperty('GITHUB_PAT');
    if (!pat) {
      Logger.log('fetchGithubDailyPrices_: REQUIRES_AUTH is true but GITHUB_PAT is not set. Skipping.');
      return {};
    }
    headers['Authorization'] = 'token ' + pat;
  }

  var response;
  try {
    response = UrlFetchApp.fetch(GITHUB_PRICE_CSV_CONFIG.RAW_URL, {
      headers: headers,
      muteHttpExceptions: true,
    });
  } catch (e) {
    Logger.log('fetchGithubDailyPrices_: fetch failed: ' + e);
    return {};
  }

  if (response.getResponseCode() !== 200) {
    Logger.log('fetchGithubDailyPrices_: HTTP ' + response.getResponseCode() + ' -- ' +
      response.getContentText().slice(0, 200));
    return {};
  }

  var rows = Utilities.parseCsv(response.getContentText().replace(/^﻿/, ''));
  if (rows.length < 2) return {};

  var head = rows[0];
  var idx = {};
  for (var c = 0; c < head.length; c++) idx[String(head[c]).trim()] = c;
  var required = ['ticker', 'date', 'close', 'updated_at', 'stale'];
  for (var r = 0; r < required.length; r++) {
    if (!(required[r] in idx)) {
      Logger.log('fetchGithubDailyPrices_: missing column ' + required[r] + ' -- schema drift?');
      return {};
    }
  }

  var out = {};
  for (var i = 1; i < rows.length; i++) {
    var row = rows[i];
    if (row.length < head.length) continue; // tail blank row
    var ticker = String(row[idx['ticker']]).trim();
    if (!ticker) continue;
    var close = parseFloat(row[idx['close']]);
    if (!isFinite(close) || close <= 0) continue;
    out[ticker] = {
      close: close,
      date: String(row[idx['date']]).trim(),
      staleFromGithub: String(row[idx['stale']]).trim().toLowerCase() === 'true',
      updatedAt: String(row[idx['updated_at']]).trim(),
    };
  }
  return out;
}

/**
 * Three-tier price resolution, extending the existing resolvePrice_(live, csv,
 * csvDate) in the main script with GitHub Actions' daily refresh as a middle
 * tier: 실시간 (live quote) > GitHub Actions 일일 갱신 > 파이프라인 CSV (기존
 * sheet_export.csv 기준종가). This is additive -- call it instead of
 * resolvePrice_() only where you want the GitHub tier considered; it does not
 * modify resolvePrice_() itself.
 */
function resolvePriceWithGithubTier_(live, github, csv, csvDate) {
  if (live !== null && live !== undefined && live > 0 && isFinite(live)) {
    return { price: live, src: '실시간', ok: true };
  }
  if (github && github.close > 0 && !github.staleFromGithub) {
    return { price: github.close, src: 'GitHub ' + github.date, ok: true, fallback: true };
  }
  if (csv !== null && csv !== undefined && csv > 0 && isFinite(csv)) {
    return { price: csv, src: 'CSV ' + (csvDate || ''), ok: true, fallback: true };
  }
  if (github && github.close > 0) {
    // Stale-but-present GitHub price beats nothing at all.
    return { price: github.close, src: 'GitHub(stale) ' + github.date, ok: true, fallback: true };
  }
  return { price: null, src: '없음', ok: false };
}
