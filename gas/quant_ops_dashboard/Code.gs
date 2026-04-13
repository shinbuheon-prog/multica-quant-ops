function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Quant Ops')
    .addItem('대시보드 새로고침', 'refreshDashboardFromDrive')
    .addItem('서식 다시 적용', 'applyDashboardFormatting')
    .addToUi();
}

function refreshDashboardFromDrive() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const configSheet = ensureSheet_(spreadsheet, 'Config');
  ensureConfigLayout_(configSheet);
  const config = readConfig_(configSheet);

  const fileId = config.dashboardExportFileId;
  if (!fileId) {
    throw new Error('Config 시트 B2 셀에 dashboard export JSON 파일 ID를 입력하세요.');
  }

  const file = DriveApp.getFileById(fileId);
  const payload = JSON.parse(file.getBlob().getDataAsString('UTF-8'));
  const dashboardItems = filterDashboardItems_(payload.dashboard || [], config);
  const batchRuns = limitItems_(payload.batch_runs || [], config.batchRunsMaxRows);
  const incidents = limitItems_(payload.incidents || [], config.incidentsMaxRows);

  writeOverviewSheet_(spreadsheet, payload, dashboardItems);
  writeDashboardSheet_(spreadsheet, dashboardItems);
  writeBatchRunsSheet_(spreadsheet, batchRuns);
  writeIncidentsSheet_(spreadsheet, incidents);
  applyDashboardFormatting();

  configSheet.getRange('B3').setValue(new Date());
}

function applyDashboardFormatting() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  formatOverviewSheet_(ensureSheet_(spreadsheet, 'Overview'));
  formatDashboardSheet_(ensureSheet_(spreadsheet, 'Dashboard'));
  formatBatchRunsSheet_(ensureSheet_(spreadsheet, 'Batch Runs'));
  formatIncidentsSheet_(ensureSheet_(spreadsheet, 'Incidents'));
}

function ensureConfigLayout_(sheet) {
  const rows = [
    ['key', 'value'],
    ['dashboard_export_file_id', ''],
    ['last_refresh_at', ''],
    ['watchlist_tickers', ''],
    ['dashboard_status_filter', 'all'],
    ['dashboard_max_rows', '20'],
    ['batch_runs_max_rows', '10'],
    ['incidents_max_rows', '10'],
  ];
  const existingRows = sheet.getLastRow();
  const existingKeys = existingRows > 0
    ? sheet.getRange(1, 1, existingRows, 2).getValues()
    : [];
  const currentValues = {};
  existingKeys.forEach(function(row) {
    const key = String(row[0] || '').trim();
    if (key) {
      currentValues[key] = row[1];
    }
  });

  const mergedRows = rows.map(function(row) {
    const key = row[0];
    return [key, Object.prototype.hasOwnProperty.call(currentValues, key) ? currentValues[key] : row[1]];
  });

  sheet.clear();
  sheet.getRange(1, 1, mergedRows.length, mergedRows[0].length).setValues(mergedRows);
  sheet.autoResizeColumns(1, 2);
}

function readConfig_(sheet) {
  const values = sheet.getRange(1, 1, sheet.getLastRow(), 2).getValues();
  const config = {};
  values.forEach(function(row) {
    const key = String(row[0] || '').trim();
    if (key) {
      config[key] = row[1];
    }
  });

  return {
    dashboardExportFileId: String(config.dashboard_export_file_id || '').trim(),
    watchlistTickers: parseTickerList_(config.watchlist_tickers),
    dashboardStatusFilter: parseStatusFilter_(config.dashboard_status_filter),
    dashboardMaxRows: parsePositiveInt_(config.dashboard_max_rows, 20),
    batchRunsMaxRows: parsePositiveInt_(config.batch_runs_max_rows, 10),
    incidentsMaxRows: parsePositiveInt_(config.incidents_max_rows, 10),
  };
}

function parseTickerList_(value) {
  return String(value || '')
    .split(',')
    .map(function(item) { return item.trim().toUpperCase(); })
    .filter(function(item) { return item !== ''; });
}

function parsePositiveInt_(value, defaultValue) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : defaultValue;
}

function parseStatusFilter_(value) {
  const normalized = String(value || 'all').trim().toLowerCase();
  if (['all', 'ready_only', 'blocked_only'].indexOf(normalized) !== -1) {
    return normalized;
  }
  return 'all';
}

function limitItems_(items, maxRows) {
  return items.slice(0, maxRows);
}

function filterDashboardItems_(items, config) {
  let filtered = items.slice();
  if (config.watchlistTickers.length > 0) {
    filtered = filtered.filter(function(item) {
      return config.watchlistTickers.indexOf(String(item.symbol || '').toUpperCase()) !== -1;
    });
  }
  if (config.dashboardStatusFilter === 'ready_only') {
    filtered = filtered.filter(function(item) {
      return Boolean(item.paper_execution_ready);
    });
  } else if (config.dashboardStatusFilter === 'blocked_only') {
    filtered = filtered.filter(function(item) {
      return Boolean(item.blocked_stage);
    });
  }
  return limitItems_(filtered, config.dashboardMaxRows);
}

function writeOverviewSheet_(spreadsheet, payload, dashboardItems) {
  const sheet = ensureSheet_(spreadsheet, 'Overview');
  const overview = payload.overview || {};
  const rows = [
    ['항목', '값'],
    ['생성 시각', payload.generated_at || ''],
    ['표시 종목 수', dashboardItems.length],
    ['준비 완료 종목 수', countReadyTickers_(dashboardItems)],
    ['차단 종목 수', countBlockedTickers_(dashboardItems)],
    ['전체 종목 수', overview.total_tickers || 0],
    ['현재 상태 필터', getCurrentStatusFilterLabel_(spreadsheet)],
    ['Alpha Vantage 사용일', overview.alpha_vantage_usage_date || ''],
    ['Alpha Vantage 사용량', overview.alpha_vantage_used_calls || ''],
    ['Alpha Vantage 일일 한도', overview.alpha_vantage_daily_limit || ''],
    ['Alpha Vantage 남은 호출', overview.alpha_vantage_remaining_calls || ''],
    ['최신 스냅샷 시각', overview.latest_market_snapshot || ''],
    ['최신 일일 리포트', overview.latest_daily_report_headline || ''],
    ['최신 일일 리포트 경로', overview.latest_daily_report_path || ''],
  ];
  writeTable_(sheet, rows);
  writeOverviewChart_(sheet);
}

function getCurrentStatusFilterLabel_(spreadsheet) {
  const configSheet = ensureSheet_(spreadsheet, 'Config');
  const config = readConfig_(configSheet);
  if (config.dashboardStatusFilter === 'ready_only') {
    return '준비 가능만';
  }
  if (config.dashboardStatusFilter === 'blocked_only') {
    return '차단 종목만';
  }
  return '전체';
}

function countReadyTickers_(items) {
  return items.filter(function(item) {
    return Boolean(item.paper_execution_ready);
  }).length;
}

function countBlockedTickers_(items) {
  return items.filter(function(item) {
    return Boolean(item.blocked_stage);
  }).length;
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
    ['우선순위', '생성 시각', '헤드라인', '요약', '경로'],
  ];

  items.forEach(function(item) {
    rows.push([
      classifyIncidentPriority_(item),
      item.generated_at || '',
      item.headline || '',
      item.details_excerpt || '',
      item.path || '',
    ]);
  });

  writeTable_(sheet, rows);
}

function classifyIncidentPriority_(item) {
  const headline = String(item.headline || '').toLowerCase();
  if (headline.indexOf('paper_execution') !== -1) {
    return '높음';
  }
  if (headline.indexOf('data_quality') !== -1) {
    return '높음';
  }
  if (headline.indexOf('backtest') !== -1) {
    return '중간';
  }
  if (headline.indexOf('no incident') !== -1) {
    return '정보';
  }
  return '확인 필요';
}

function ensureSheet_(spreadsheet, name) {
  const existing = spreadsheet.getSheetByName(name);
  return existing || spreadsheet.insertSheet(name);
}

function writeTable_(sheet, rows) {
  sheet.clear();
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sheet.autoResizeColumns(1, rows[0].length);
}

function formatOverviewSheet_(sheet) {
  if (sheet.getLastRow() < 2) {
    return;
  }

  const headerRange = sheet.getRange(1, 1, 1, 2);
  headerRange
    .setFontWeight('bold')
    .setBackground('#1f2937')
    .setFontColor('#ffffff');

  sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).setFontWeight('bold');
  sheet.setFrozenRows(1);
}

function formatDashboardSheet_(sheet) {
  if (sheet.getLastRow() < 2) {
    return;
  }

  const headerRange = sheet.getRange(1, 1, 1, sheet.getLastColumn());
  headerRange
    .setFontWeight('bold')
    .setBackground('#0f766e')
    .setFontColor('#ffffff');

  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(1);
  sheet.getRange(2, 4, sheet.getLastRow() - 1, 1).setNumberFormat('0.00');
  sheet.getRange(2, 5, sheet.getLastRow() - 1, 1).setNumberFormat('0.00%');
  sheet.getRange(2, 7, sheet.getLastRow() - 1, 1).setNumberFormat('0.0000');
  sheet.getRange(2, 11, sheet.getLastRow() - 1, 1).setNumberFormat('0');
  sheet.setColumnWidths(10, 4, 220);

  const dataRange = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn());
  const values = dataRange.getValues();
  const backgrounds = values.map(function(row) {
    const readyValue = row[7];
    const blockedStage = row[8];
    const remainingCalls = Number(row[10] || 0);
    let color = '#ffffff';

    if (readyValue === '가능') {
      color = '#dcfce7';
    } else if (blockedStage && blockedStage !== '없음') {
      color = '#fee2e2';
    } else if (remainingCalls > 0 && remainingCalls <= 5) {
      color = '#fef3c7';
    }

    return new Array(sheet.getLastColumn()).fill(color);
  });
  dataRange.setBackgrounds(backgrounds);
}

function formatBatchRunsSheet_(sheet) {
  if (sheet.getLastRow() < 2) {
    return;
  }

  const headerRange = sheet.getRange(1, 1, 1, sheet.getLastColumn());
  headerRange
    .setFontWeight('bold')
    .setBackground('#1d4ed8')
    .setFontColor('#ffffff');

  sheet.setFrozenRows(1);
  sheet.setColumnWidths(6, 2, 260);

  const dataRange = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn());
  const values = dataRange.getValues();
  const backgrounds = values.map(function(row) {
    const readyCount = Number(row[3] || 0);
    const blockedCount = Number(row[4] || 0);
    let color = '#ffffff';

    if (readyCount > 0 && blockedCount === 0) {
      color = '#dcfce7';
    } else if (blockedCount > 0) {
      color = '#fee2e2';
    }

    return new Array(sheet.getLastColumn()).fill(color);
  });
  dataRange.setBackgrounds(backgrounds);
}

function formatIncidentsSheet_(sheet) {
  if (sheet.getLastRow() < 2) {
    return;
  }

  const headerRange = sheet.getRange(1, 1, 1, sheet.getLastColumn());
  headerRange
    .setFontWeight('bold')
    .setBackground('#7c2d12')
    .setFontColor('#ffffff');

  sheet.setFrozenRows(1);
  sheet.setColumnWidths(3, 2, 300);

  const dataRange = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn());
  const values = dataRange.getValues();
  const backgrounds = values.map(function(row) {
    const priority = row[0];
    let color = '#ffffff';

    if (priority === '높음') {
      color = '#fee2e2';
    } else if (priority === '중간') {
      color = '#fef3c7';
    } else if (priority === '정보') {
      color = '#e0f2fe';
    }

    return new Array(sheet.getLastColumn()).fill(color);
  });
  dataRange.setBackgrounds(backgrounds);
}

function writeOverviewChart_(sheet) {
  sheet.getCharts().forEach(function(chart) {
    sheet.removeChart(chart);
  });

  if (sheet.getLastRow() < 5) {
    return;
  }

  const chartRange = sheet.getRange('A3:B5');
  const chart = sheet.newChart()
    .setChartType(Charts.ChartType.COLUMN)
    .addRange(chartRange)
    .setPosition(2, 4, 0, 0)
    .setOption('title', '준비 상태 요약')
    .setOption('legend', { position: 'none' })
    .setOption('colors', ['#0f766e'])
    .build();

  sheet.insertChart(chart);
}
