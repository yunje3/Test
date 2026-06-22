# 팀 예산 관리 시스템 - Streamlit + Apps Script + Google Sheets

기존 서비스 계정 방식 대신 Google Apps Script Web App을 API 서버처럼 사용합니다.
복잡한 Google Cloud 서비스 계정 JSON 인증 없이, Google Sheet 안에 Apps Script를 붙여서 배포하면 Streamlit에서 데이터를 읽고 씁니다.

## 구조

```text
Streamlit 앱
  ↓ HTTP 요청
Apps Script Web App
  ↓ SpreadsheetApp
Google Sheets
```

## 저장소 구조

```text
budget_streamlit_apps_script/
├─ app.py
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ apps_script/
│  └─ Code.gs
└─ .streamlit/
   └─ secrets.toml.example
```

## 1. Google Sheet 만들기

1. Google Sheets에서 새 스프레드시트를 만듭니다.
2. 하단 시트 이름은 `budget_records`로 만들면 좋습니다.
3. 시트가 없어도 Apps Script가 자동 생성합니다.

## 2. Apps Script 붙여넣기

1. Google Sheet를 엽니다.
2. `확장 프로그램` > `Apps Script`를 클릭합니다.
3. `apps_script/Code.gs` 내용을 복사해서 Apps Script 편집기의 `Code.gs`에 붙여넣습니다.
4. 저장합니다.

## 3. Apps Script 배포

1. Apps Script 편집기 오른쪽 위의 `배포`를 누릅니다.
2. `새 배포`를 누릅니다.
3. 유형 선택에서 `웹 앱`을 선택합니다.
4. 설정은 아래처럼 둡니다.

```text
설명: budget api
실행 사용자: 나
액세스 권한: 모든 사용자
```

5. 배포를 누릅니다.
6. 처음에는 Google 권한 승인 화면이 나옵니다. 본인 계정으로 승인합니다.
7. 배포가 끝나면 `웹 앱 URL`을 복사합니다.

## 4. Streamlit secrets 설정

로컬 실행용으로 아래 파일을 만듭니다.

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

`.streamlit/secrets.toml`에 Apps Script Web App URL을 넣습니다.

```toml
[apps_script]
web_app_url = "https://script.google.com/macros/s/배포_ID/exec"
api_key = ""
```

`api_key`는 선택 사항입니다. 처음에는 비워둬도 됩니다.

## 5. 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 보통 아래 주소로 열립니다.

```text
http://localhost:8501
```

## 6. GitHub 업로드

```bash
git init
git add .
git commit -m "Add Streamlit Apps Script budget system"
git branch -M main
git remote add origin https://github.com/깃허브아이디/저장소명.git
git push -u origin main
```

주의: `.streamlit/secrets.toml`은 GitHub에 올리면 안 됩니다. `.gitignore`에 이미 제외 처리되어 있습니다.

## 7. Streamlit Community Cloud 배포

1. Streamlit Community Cloud에서 새 앱을 만듭니다.
2. GitHub 저장소를 선택합니다.
3. Main file path는 `app.py`로 지정합니다.
4. Secrets 영역에 아래 내용을 붙여넣습니다.

```toml
[apps_script]
web_app_url = "https://script.google.com/macros/s/배포_ID/exec"
api_key = ""
```

5. Deploy를 누릅니다.

## 선택 보안: API Key 사용

Apps Script Web App을 `모든 사용자` 접근으로 열기 때문에 URL을 아는 사람이 요청할 수 있습니다.
내부용이라도 최소한의 보호를 하려면 API Key를 쓰는 것이 좋습니다.

### Apps Script 쪽

Apps Script 편집기에서 `프로젝트 설정` > `스크립트 속성`에 아래 값을 추가합니다.

```text
속성: APP_KEY
값: 원하는_긴_문자열
```

또는 `Code.gs`의 `CONFIG.APP_KEY`에 직접 넣을 수도 있지만, GitHub에 올리는 코드에는 실제 키를 넣지 마세요.

### Streamlit 쪽

`.streamlit/secrets.toml` 또는 Streamlit Cloud Secrets에 같은 값을 넣습니다.

```toml
[apps_script]
web_app_url = "https://script.google.com/macros/s/배포_ID/exec"
api_key = "원하는_긴_문자열"
```

## 시트 컬럼 구조

앱이 자동으로 아래 헤더를 생성합니다.

| 컬럼 | 설명 |
|---|---|
| id | 기록 고유 ID |
| used_date | 사용일 |
| month | 사용월 |
| member | 팀원 |
| category | 예산 항목 |
| amount | 사용 금액 |
| title | 내용 |
| memo | 메모 |
| created_at | 생성일 |
| updated_at | 수정일 |
