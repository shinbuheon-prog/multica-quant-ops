// Reference code, not auto-deployed by this repository.
//
// Extends the Phase 10 GitHub bridge idea (see github_price_source.gs in this
// same folder) from "daily prices only" to the *whole* metrics sheet
// (sheet_export.csv -- 티커/투자점수/건전성등급/핵심배수/... all 27 columns).
// Today refreshMetrics() in the live Apps Script project
// (/home/claude/gas/Code.gs in the Cowork session, ~2,100 lines, not in this
// repo) reads sheet_export.csv from Google Drive, which means someone has to
// manually re-upload it (or a Cowork scheduled task with Drive MCP access has
// to wake up and do it) every time the pipeline produces a new one -- see
// build_drive_manifest.py's module docstring for exactly why that dependency
// exists. This file removes that step: Apps Script pulls the CSV straight
// from raw.githubusercontent.com on its own schedule, no Drive upload and no
// Cowork session in the loop for *delivery*.
//
// This is NOT wired into the live sheet automatically, for the same reason
// as github_price_source.gs: saving Apps Script code takes effect
// immediately with no review step, and this repo/session has no way to test
// Apps Script execution. Paste it into the *existing* Apps Script project
// behind the Cowork sheet as a new, separate file, review it, and run
// refreshMetricsFromGithub() manually once before deciding whether to swap
// it in for refreshMetrics() (or wire it into a menu item / time trigger).
// It intentionally mirrors refreshMetrics()'s own validation logic line for
// line rather than refactoring the original -- see "왜 로직을 따로 두는가"
// below.
//
// ---------------------------------------------------------------------------
// Prerequisite decision this repo cannot make for you (same as
// github_price_source.gs): is shinbuheon-prog/multica-quant-ops public or
// private?
//   - Public repo: UrlFetchApp can hit raw.githubusercontent.com with no
//     credential.
//   - Private repo: UrlFetchApp needs an Authorization: token <PAT> header.
//     Store the PAT in this Apps Script project's Script Properties
//     (File > Project properties > Script properties) under a key like
//     GITHUB_PAT -- never hard-code it in this file. A fine-grained PAT with
//     read-only "Contents" access to just this repo is enough.
// ---------------------------------------------------------------------------
//
// Prerequisite this repo *also* cannot do for you: ops/fundamentals/
// sheet_export.csv in this repo has to actually be kept fresh. As of this
// writing it holds a single one-time snapshot (commit e43e599, 2026-09-03).
// The Cowork VM that runs the pipeline has no git push credentials for this
// repo (push happens from the user's own machine) -- see
// /home/claude/sync_sheet_export_to_repo.sh in that session, which copies
// the freshly-generated sheet_export.csv into this repo path and leaves it
// staged for review, but does not commit or push. Until someone pushes a
// fresh copy after each pipeline run, this bridge will serve a stale file --
// it degrades safely (see fetchGithubSheetExportCsv_ below) but "stale"
// here means "as old as the last git push", not "as old as the last
// pipeline run".
//
// 왜 로직을 따로 두는가 (why this duplicates refreshMetrics()'s validation
// instead of extracting a shared helper): the existing convention in this
// folder (see github_price_source.gs's own header comment) is to never
// touch the functions already live in Code.gs -- this file only adds beside
// them. Refactoring refreshMetrics() to share code with this function would
// mean editing the live production script, which is exactly what this
// reference-code pattern is designed to avoid until a human has reviewed
// and pasted it in deliberately. The duplication is small (one CSV-shape
// validation block) and it does reuse the *global* symbols that already
// exist once this file sits in the same Apps Script project -- REQUIRED_
// METRIC_COLS, CFG, sheet_(), writeMeta_(), audit_(), stamp_(), ss_() --
// so if those globals ever change shape, this function automatically picks
// up the new definition rather than drifting from a stale copy.

var GITHUB_SHEET_EXPORT_CONFIG = {
  // Change 'main' if the workflow/commits land on a different branch.
  RAW_URL: 'https://raw.githubusercontent.com/shinbuheon-prog/multica-quant-ops/main/ops/fundamentals/sheet_export.csv',
  // Set true only after confirming the repo is private and GITHUB_PAT is set
  // in Script Properties.
  REQUIRES_AUTH: false,
};

/**
 * Fetch raw sheet_export.csv text from GitHub. Never throws -- returns null
 * on any fetch/HTTP/auth failure, with the reason logged via Logger.log, so
 * a GitHub outage or a stale/missing PAT degrades to "couldn't refresh from
 * GitHub this time" rather than crashing the caller.
 *
 * Returns { csv: <string, BOM stripped>, lastModified: <string|null> } on
 * success. lastModified comes from the HTTP response header when GitHub's
 * CDN sends one -- raw.githubusercontent.com does not always include it, so
 * treat a null here as "unknown", not "never updated".
 */
function fetchGithubSheetExportCsv_() {
  var headers = {};
  if (GITHUB_SHEET_EXPORT_CONFIG.REQUIRES_AUTH) {
    var pat = PropertiesService.getScriptProperties().getProperty('GITHUB_PAT');
    if (!pat) {
      Logger.log('fetchGithubSheetExportCsv_: REQUIRES_AUTH is true but GITHUB_PAT is not set. Skipping.');
      return null;
    }
    headers['Authorization'] = 'token ' + pat;
  }

  var response;
  try {
    response = UrlFetchApp.fetch(GITHUB_SHEET_EXPORT_CONFIG.RAW_URL, {
      headers: headers,
      muteHttpExceptions: true,
    });
  } catch (e) {
    Logger.log('fetchGithubSheetExportCsv_: fetch failed: ' + e);
    return null;
  }

  if (response.getResponseCode() !== 200) {
    Logger.log('fetchGithubSheetExportCsv_: HTTP ' + response.getResponseCode() + ' -- ' +
      response.getContentText().slice(0, 200));
    return null;
  }

  var text = response.getContentText('UTF-8').replace(/^﻿/, '');
  var lastModified = null;
  try {
    var h = response.getAllHeaders();
    lastModified = h['Last-Modified'] || h['last-modified'] || null;
  } catch (e) {
    // getAllHeaders() is best-effort -- absence of a timestamp is not a failure.
  }
  return { csv: text, lastModified: lastModified };
}

/**
 * GitHub-sourced twin of refreshMetrics() (Code.gs). Same validation, same
 * "검증을 덮어쓰기 전에 한다" rule (nothing is written to the 지표 sheet
 * unless the fetched CSV passes every check refreshMetrics() itself would
 * apply), same REQUIRED_METRIC_COLS gate so an old/malformed export can't
 * silently wipe the sheet. The only thing that changes is where the CSV
 * text comes from: raw.githubusercontent.com instead of DriveApp.
 *
 * Run this manually from the Apps Script editor first and check the 지표
 * sheet + Logger output before wiring it into a menu item or a time-driven
 * trigger in place of (or alongside) refreshMetrics().
 */
function refreshMetricsFromGithub() {
  var fetched = fetchGithubSheetExportCsv_();
  if (!fetched) {
    throw new Error('GitHub에서 sheet_export.csv를 가져오지 못했습니다 (Logger 로그 확인). ' +
      '(지표 시트는 그대로입니다 -- 덮어쓰지 않았습니다)');
  }

  var rows = Utilities.parseCsv(fetched.csv);
  if (rows.length < 2) throw new Error('CSV에 데이터 행이 없습니다. (덮어쓰지 않았습니다)');

  var head = rows[0].map(function (h) { return String(h).trim(); });
  var W = head.length;
  var missing = REQUIRED_METRIC_COLS.filter(function (c) { return head.indexOf(c) < 0; });
  if (missing.length) {
    audit_('refreshMetricsFromGithub', 'NG', '필수 열 누락: ' + missing.join(', '));
    throw new Error('CSV에 필수 열이 없습니다: ' + missing.join(', ') +
      '\n(덮어쓰지 않았습니다 -- 기존 지표는 그대로입니다)');
  }

  // setValues는 직사각형만 받는다 -- refreshMetrics()와 동일한 이유로 양쪽(짧은 행 채움 ·
  // 헤더보다 긴 행은 에러) 다 방어한다.
  var body = [], i, j;
  for (i = 1; i < rows.length; i++) {
    var r = rows[i], empty = true;
    for (j = 0; j < r.length; j++) if (String(r[j]).trim() !== '') { empty = false; break; }
    if (empty) continue;
    if (r.length > W)
      throw new Error('CSV ' + (i + 1) + '행의 열 수(' + r.length + ')가 머리글(' + W + ')보다 많습니다.' +
        '\n(덮어쓰지 않았습니다)');
    var row = [];
    for (j = 0; j < W; j++) row.push(j < r.length ? r[j] : '');
    body.push(row);
  }
  if (!body.length) throw new Error('CSV에 실제 데이터 행이 없습니다. (덮어쓰지 않았습니다)');

  var ti = head.indexOf('티커'), dup = {}, dups = [];
  for (i = 0; i < body.length; i++) {
    var t = String(body[i][ti]).trim();
    if (!t) continue;
    if (dup[t]) dups.push(t); else dup[t] = 1;
  }
  if (dups.length) throw new Error('CSV에 티커가 중복입니다: ' + dups.slice(0, 5).join(', ') +
    '\n(덮어쓰지 않았습니다)');

  var out = [head].concat(body);
  var s = sheet_(CFG.SHEET_METRICS);
  s.clear();
  if (W > s.getMaxColumns()) s.insertColumnsAfter(s.getMaxColumns(), W - s.getMaxColumns());
  if (out.length > s.getMaxRows()) s.insertRowsAfter(s.getMaxRows(), out.length - s.getMaxRows());
  s.getRange(1, 1, out.length, W).setValues(out);
  s.getRange(1, 1, 1, W).setFontWeight('bold');
  s.setFrozenRows(1);
  rows = out;

  writeMeta_({
    '지표 파일': 'GitHub raw (' + GITHUB_SHEET_EXPORT_CONFIG.RAW_URL + ')',
    '지표 파일 갱신': fetched.lastModified || '확인불가 (GitHub raw가 Last-Modified 헤더를 안 줄 때가 있음)',
    '지표 불러온 시각': stamp_(new Date()),
    '지표 행수': rows.length - 1,
  });
  audit_('refreshMetricsFromGithub', 'OK', (rows.length - 1) + '행 (GitHub 소스, Drive 안 거침)');
  ss_().toast('지표 ' + (rows.length - 1) + '행 갱신 (GitHub raw 소스)');
}
