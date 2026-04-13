function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Quant Ops')
    .addItem('대시보드 새로고침', 'refreshDashboardFromDrive')
    .addToUi();
}

function refreshDashboardFromDrive() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ensureSheet_(spreadsheet, 'Config');
  ensureConfigLayout_(configSheet);

  const fileId = String(configSheet.getRange('B2').getValue()).trim();
  if (!fileId) {
    throw new Error('Config 시트 B2 셀에 dashboard export JSON 파일 ID를 입력하세요.');
  }

  const file = DriveApp.getFileById(fileId);
  const payload = JSON.parse(file.getBlob().getDataAsString('UTF-8'));

  writeOverviewSheet_(spreadsheet, payload);
  writeDashboardSheet_(spreadsheet, payload.dashboard || []);
  writeBatchRunsSheet_(spreadsheet, payload.batch_runs || []);
  writeIncidentsSheet_(spreadsheet, payload.incidents || []);

  configSheet.getRange('B3').setValue(new Date());
}

function ensureConfigLayout_(sheet) {
  const rows = [
    ['key', 'value'],
    ['dashboard_export_file_id', ''],
    ['last_refresh_at', ''],
  ];
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
}

function writeOverviewSheet_(spreadsheet, payload) {
  const sheet = ensureSheet_(spreadsheet, 'Overview');
  const overview = payload.overview || {};
  const rows = [
    ['항목', '값'],
    ['생성 시각', payload.generated_at || ''],
    ['종목 수', overview.total_tickers || 0],
    ['준비 완료 종목 수', overview.ready_tickers || 0],
    ['차단 종목 수', overview.blocked_tickers || 0],
    ['Alpha Vantage 사용일', overview.alpha_vantage_usage_date || ''],
    ['Alpha Vantage 사용량', overview.alpha_vantage_used_calls || ''],
    ['Alpha Vantage 일일 한도', overview.alpha_vantage_daily_limit || ''],
    ['Alpha Vantage 남은 호출', overview.alpha_vantage_remaining_calls || ''],
    ['최신 스냅샷 시각', overview.latest_market_snapshot || ''],
    ['최신 일일 리포트', overview.latest_daily_report_headline || ''],
    ['최신 일일 리포트 경로', overview.latest_daily_report_path || ''],
  ];
  writeTable_(sheet, rows);
}

function writeDashboardSheet_(spreadsheet, items) {
  const sheet = ensureSheet_(spreadsheet, 'Dashboard');
  const rows = [
    [
      '티커',
      '생성 시각',
      '소스',
      '현재가',
      '등락률',
      '시그널',
      '신뢰도',
      '페이퍼 실행 준비',
      '차단 단계',
      '운영 헤드라인',
      '남은 호출',
      '리포트 요약',
      '리포트 경로',
    ],
  ];

  items.forEach(function(item) {
    rows.push([
      item.symbol || '',
      item.generated_at || '',
      item.source || '',
      item.current_price || '',
      item.change_percent || '',
      item.signal_direction || '',
      item.signal_confidence || '',
      item.paper_execution_ready ? '가능' : '보류',
      item.blocked_stage || '없음',
      item.incident_headline || '',
      item.remaining_calls || '',
      item.report_excerpt || '',
      item.report_path || '',
    ]);
  });

  writeTable_(sheet, rows);
}

function writeBatchRunsSheet_(spreadsheet, items) {
  const sheet = ensureSheet_(spreadsheet, 'Batch Runs');
  const rows = [
    [
      '배치명',
      '생성 시각',
      '종목 수',
      '준비 완료 수',
      '차단 수',
      '요약 경로',
      '운영 요약',
    ],
  ];

  items.forEach(function(item) {
    rows.push([
      item.batch_name || '',
      item.generated_at || '',
      item.ticker_count || '',
      item.ready_count || '',
      item.blocked_count || '',
      item.summary_report_path || '',
      item.summary_report_excerpt || '',
    ]);
  });

  writeTable_(sheet, rows);
}

function writeIncidentsSheet_(spreadsheet, items) {
  const sheet = ensureSheet_(spreadsheet, 'Incidents');
  const rows = [
    ['생성 시각', '헤드라인', '요약', '경로'],
  ];

  items.forEach(function(item) {
    rows.push([
      item.generated_at || '',
      item.headline || '',
      item.details_excerpt || '',
      item.path || '',
    ]);
  });

  writeTable_(sheet, rows);
}

function ensureSheet_(spreadsheet, name) {
  const existing = spreadsheet.getSheetByName(name);
  return existing || spreadsheet.insertSheet(name);
}

function writeTable_(sheet, rows) {
  sheet.clearContents();
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sheet.autoResizeColumns(1, rows[0].length);
}
