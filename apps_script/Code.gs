/**
 * 팀 예산 관리 시스템 - Google Apps Script API
 *
 * 사용 방법:
 * 1) Google Sheets 파일 열기
 * 2) 확장 프로그램 > Apps Script
 * 3) 이 파일 내용을 Code.gs에 붙여넣기
 * 4) 배포 > 새 배포 > 웹 앱
 * 5) 실행 사용자: 나, 액세스 권한: 모든 사용자
 */

const CONFIG = {
  // Google Sheet 안의 시트 이름입니다. 없으면 자동 생성됩니다.
  SHEET_NAME: 'budget_records',

  // 스프레드시트에 묶인 Apps Script로 만들면 비워둬도 됩니다.
  // 독립형 Apps Script로 만들었다면 Spreadsheet ID를 넣어주세요.
  SPREADSHEET_ID: '',

  // 선택 보안 키입니다.
  // 비워두면 키 검사를 하지 않습니다.
  // 더 안전하게 쓰려면 Apps Script의 프로젝트 설정 > 스크립트 속성에 APP_KEY를 저장하세요.
  APP_KEY: '',
};

const HEADERS = [
  'id',
  'used_date',
  'month',
  'member',
  'category',
  'amount',
  'title',
  'memo',
  'created_at',
  'updated_at',
];

function doGet(e) {
  return handleRequest_(e);
}

function doPost(e) {
  return handleRequest_(e);
}

function handleRequest_(e) {
  try {
    const request = parseRequest_(e);
    verifyApiKey_(request);

    const action = request.action || 'list';

    if (action === 'health') {
      const sheet = getSheet_();
      return json_({ ok: true, message: 'ok', sheet_name: sheet.getName() });
    }

    if (action === 'list') {
      return json_({ ok: true, records: listRecords_() });
    }

    if (action === 'add') {
      const record = addRecord_(request.record || {});
      return json_({ ok: true, record });
    }

    if (action === 'delete') {
      const deleted = deleteRecord_(request.id || request.record_id || '');
      return json_({ ok: true, deleted });
    }

    if (action === 'clear') {
      clearRecords_();
      return json_({ ok: true });
    }

    throw new Error('지원하지 않는 action입니다: ' + action);
  } catch (error) {
    return json_({ ok: false, error: String(error && error.message ? error.message : error) });
  }
}

function parseRequest_(e) {
  let data = {};

  if (e && e.postData && e.postData.contents) {
    const content = e.postData.contents;
    try {
      data = JSON.parse(content);
    } catch (error) {
      data = {};
    }
  }

  if (e && e.parameter) {
    Object.keys(e.parameter).forEach(function (key) {
      if (data[key] === undefined) {
        data[key] = e.parameter[key];
      }
    });
  }

  return data;
}

function getConfiguredApiKey_() {
  const scriptKey = PropertiesService.getScriptProperties().getProperty('APP_KEY') || '';
  return scriptKey || CONFIG.APP_KEY || '';
}

function verifyApiKey_(request) {
  const configuredKey = getConfiguredApiKey_();
  if (!configuredKey) {
    return;
  }

  const requestKey = request.api_key || '';
  if (requestKey !== configuredKey) {
    throw new Error('API Key가 일치하지 않습니다.');
  }
}

function getSpreadsheet_() {
  if (CONFIG.SPREADSHEET_ID) {
    return SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  }

  const active = SpreadsheetApp.getActiveSpreadsheet();
  if (!active) {
    throw new Error('활성 스프레드시트를 찾지 못했습니다. CONFIG.SPREADSHEET_ID를 입력해주세요.');
  }

  return active;
}

function getSheet_() {
  const spreadsheet = getSpreadsheet_();
  let sheet = spreadsheet.getSheetByName(CONFIG.SHEET_NAME);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(CONFIG.SHEET_NAME);
  }

  ensureHeader_(sheet);
  return sheet;
}

function ensureHeader_(sheet) {
  const currentHeaders = sheet.getRange(1, 1, 1, HEADERS.length).getValues()[0];
  const isSame = HEADERS.every(function (header, index) {
    return currentHeaders[index] === header;
  });

  if (!isSame) {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.setFrozenRows(1);
  }
}

function listRecords_() {
  const sheet = getSheet_();
  const lastRow = sheet.getLastRow();

  if (lastRow <= 1) {
    return [];
  }

  const rows = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();
  const records = [];

  rows.forEach(function (row) {
    const record = {};
    HEADERS.forEach(function (header, index) {
      record[header] = normalizeValue_(row[index]);
    });

    if (String(record.id || '').trim() !== '') {
      records.push(record);
    }
  });

  return records;
}

function addRecord_(inputRecord) {
  const sheet = getSheet_();
  const now = formatDateTime_(new Date());
  const usedDate = String(inputRecord.used_date || formatDate_(new Date())).slice(0, 10);

  const record = {
    id: inputRecord.id || Utilities.getUuid().replace(/-/g, '').slice(0, 12),
    used_date: usedDate,
    month: inputRecord.month || usedDate.slice(0, 7),
    member: inputRecord.member || '',
    category: inputRecord.category || '',
    amount: Number(inputRecord.amount || 0),
    title: inputRecord.title || '',
    memo: inputRecord.memo || '',
    created_at: inputRecord.created_at || now,
    updated_at: inputRecord.updated_at || now,
  };

  sheet.appendRow(HEADERS.map(function (header) {
    return record[header];
  }));

  return record;
}

function deleteRecord_(recordId) {
  const id = String(recordId || '').trim();
  if (!id) {
    throw new Error('삭제할 id가 없습니다.');
  }

  const sheet = getSheet_();
  const lastRow = sheet.getLastRow();

  if (lastRow <= 1) {
    return false;
  }

  const idRange = sheet.getRange(2, 1, lastRow - 1, 1);
  const found = idRange.createTextFinder(id).matchEntireCell(true).findNext();

  if (!found) {
    return false;
  }

  sheet.deleteRow(found.getRow());
  return true;
}

function clearRecords_() {
  const sheet = getSheet_();
  const lastRow = sheet.getLastRow();

  if (lastRow > 1) {
    sheet.getRange(2, 1, lastRow - 1, HEADERS.length).clearContent();
  }

  ensureHeader_(sheet);
}

function normalizeValue_(value) {
  if (value instanceof Date) {
    return formatDateTime_(value);
  }

  if (value === null || value === undefined) {
    return '';
  }

  return value;
}

function formatDate_(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

function formatDateTime_(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
}

function json_(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
