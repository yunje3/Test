/**
 * Streamlit 예산관리 시스템용 Google Apps Script API
 *
 * 사용 방법
 * 1. Google Sheet 열기
 * 2. 확장 프로그램 > Apps Script
 * 3. 이 파일 내용을 Code.gs에 붙여넣기
 * 4. 배포 > 새 배포 > 웹 앱
 *    - 실행 사용자: 나
 *    - 액세스 권한: 모든 사용자
 * 5. 웹 앱 URL을 Streamlit app.py의 DEFAULT_WEB_APP_URL에 입력
 */

const SHEET_NAME = 'budget_records';
const HEADERS = [
  'id',
  'date',
  'month',
  'member',
  'category',
  'amount',
  'title',
  'memo',
  'created_at'
];

function doGet(e) {
  try {
    validateApiKey_(e);
    const action = getParam_(e, 'action', 'list');

    if (action === 'health') {
      return json_({ ok: true, message: 'ok' });
    }

    if (action === 'list') {
      const records = readRecords_();
      return json_({ ok: true, records: records });
    }

    return json_({ ok: false, message: 'Unknown action: ' + action });
  } catch (error) {
    return json_({ ok: false, message: String(error) });
  }
}

function doPost(e) {
  try {
    const body = parseBody_(e);
    validateApiKeyFromBody_(body);

    const action = body.action || '';

    if (action === 'add') {
      const record = body.record || {};
      const saved = addRecord_(record);
      return json_({ ok: true, record: saved });
    }

    if (action === 'delete') {
      const id = String(body.id || '');
      deleteRecord_(id);
      return json_({ ok: true });
    }

    if (action === 'clear') {
      clearRecords_();
      return json_({ ok: true });
    }

    return json_({ ok: false, message: 'Unknown action: ' + action });
  } catch (error) {
    return json_({ ok: false, message: String(error) });
  }
}

function getSheet_() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(SHEET_NAME);
  }

  const firstRow = sheet.getRange(1, 1, 1, HEADERS.length).getValues()[0];
  const hasHeaders = firstRow.join('') !== '';

  if (!hasHeaders) {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.setFrozenRows(1);
  } else {
    const normalized = firstRow.slice(0, HEADERS.length).map(String);
    if (normalized.join('|') !== HEADERS.join('|')) {
      sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
      sheet.setFrozenRows(1);
    }
  }

  return sheet;
}

function readRecords_() {
  const sheet = getSheet_();
  const lastRow = sheet.getLastRow();

  if (lastRow < 2) {
    return [];
  }

  const values = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();

  return values
    .filter(row => String(row[0] || '') !== '')
    .map(row => {
      const record = {};
      HEADERS.forEach((header, index) => {
        let value = row[index];
        if (value instanceof Date) {
          value = Utilities.formatDate(value, Session.getScriptTimeZone(), 'yyyy-MM-dd');
        }
        record[header] = value;
      });
      record.amount = Number(record.amount || 0);
      return record;
    });
}

function addRecord_(record) {
  const sheet = getSheet_();
  const now = new Date();
  const dateText = String(record.date || Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd'));
  const monthText = String(record.month || dateText.substring(0, 7));

  const saved = {
    id: String(Date.now()) + '-' + String(Math.floor(Math.random() * 100000)),
    date: dateText,
    month: monthText,
    member: String(record.member || ''),
    category: String(record.category || ''),
    amount: Number(record.amount || 0),
    title: String(record.title || ''),
    memo: String(record.memo || ''),
    created_at: Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')
  };

  if (!saved.member) {
    throw new Error('팀원 값이 비어있습니다.');
  }
  if (!saved.category) {
    throw new Error('예산 항목 값이 비어있습니다.');
  }
  if (!saved.title) {
    throw new Error('내용 값이 비어있습니다.');
  }
  if (!saved.amount || saved.amount <= 0) {
    throw new Error('금액은 0보다 커야 합니다.');
  }

  const row = HEADERS.map(header => saved[header]);
  sheet.appendRow(row);
  return saved;
}

function deleteRecord_(id) {
  if (!id) {
    throw new Error('삭제할 id가 없습니다.');
  }

  const sheet = getSheet_();
  const lastRow = sheet.getLastRow();

  if (lastRow < 2) {
    return;
  }

  const ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
  for (let i = ids.length - 1; i >= 0; i--) {
    if (String(ids[i][0]) === id) {
      sheet.deleteRow(i + 2);
      return;
    }
  }

  throw new Error('해당 id를 찾을 수 없습니다: ' + id);
}

function clearRecords_() {
  const sheet = getSheet_();
  const lastRow = sheet.getLastRow();

  if (lastRow >= 2) {
    sheet.getRange(2, 1, lastRow - 1, HEADERS.length).clearContent();
  }
}

function parseBody_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return {};
  }

  try {
    return JSON.parse(e.postData.contents);
  } catch (error) {
    throw new Error('JSON 파싱 실패: ' + error);
  }
}

function getParam_(e, name, defaultValue) {
  if (!e || !e.parameter || e.parameter[name] === undefined) {
    return defaultValue;
  }
  return e.parameter[name];
}

function validateApiKey_(e) {
  const savedKey = PropertiesService.getScriptProperties().getProperty('APP_KEY');
  if (!savedKey) {
    return;
  }

  const requestKey = getParam_(e, 'api_key', '');
  if (requestKey !== savedKey) {
    throw new Error('API key가 올바르지 않습니다.');
  }
}

function validateApiKeyFromBody_(body) {
  const savedKey = PropertiesService.getScriptProperties().getProperty('APP_KEY');
  if (!savedKey) {
    return;
  }

  const requestKey = String(body.api_key || '');
  if (requestKey !== savedKey) {
    throw new Error('API key가 올바르지 않습니다.');
  }
}

function json_(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
