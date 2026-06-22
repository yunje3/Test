# 팀 예산 관리 시스템 - Streamlit + Apps Script 버전

이 버전은 `.streamlit/secrets.toml`을 사용하지 않습니다.

Apps Script Web App URL을 `app.py` 안에 직접 넣어서 GitHub에 올리고, Streamlit Cloud에서 바로 실행하는 방식입니다.

## 1. 구성 파일

```text
budget_streamlit_apps_script_hardcoded/
├─ app.py
├─ requirements.txt
├─ README.md
├─ .gitignore
└─ apps_script/
   └─ Code.gs
```

## 2. Google Sheet 만들기

Google 스프레드시트를 하나 만듭니다.

시트 이름은 자동으로 생성되므로 직접 만들지 않아도 됩니다.
자동 생성되는 시트명은 아래와 같습니다.

```text
budget_records
```

## 3. Apps Script 설정

Google Sheet에서 아래 메뉴로 들어갑니다.

```text
확장 프로그램 → Apps Script
```

`apps_script/Code.gs` 내용을 전부 복사해서 Apps Script의 `Code.gs`에 붙여넣습니다.

## 4. Apps Script 웹 앱 배포

Apps Script 화면 오른쪽 위에서 아래 순서로 진행합니다.

```text
배포 → 새 배포 → 유형 선택 → 웹 앱
```

설정값은 아래처럼 합니다.

```text
실행 사용자: 나
액세스 권한: 모든 사용자
```

배포 후 나오는 웹 앱 URL을 복사합니다.

예시:

```text
https://script.google.com/macros/s/AKfycbxxxxxxxxxxxxxxxxxxxx/exec
```

## 5. app.py에 URL 직접 입력

`app.py` 파일 상단에서 아래 부분을 찾습니다.

```python
DEFAULT_WEB_APP_URL = ""
```

복사한 Apps Script 웹 앱 URL을 넣습니다.

```python
DEFAULT_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxxxxxxxxxxxxxxxxxxxx/exec"
```

처음에는 API Key를 비워둡니다.

```python
DEFAULT_API_KEY = ""
```

## 6. 로컬 실행

### Mac / Linux

```bash
cd budget_streamlit_apps_script_hardcoded
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Windows PowerShell

```powershell
cd budget_streamlit_apps_script_hardcoded
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 보통 아래 주소로 열립니다.

```text
http://localhost:8501
```

## 7. GitHub 업로드

GitHub 저장소를 만든 뒤 아래처럼 업로드합니다.

```bash
git init
git add .
git commit -m "Add Streamlit Apps Script budget system"
git branch -M main
git remote add origin https://github.com/깃허브아이디/저장소명.git
git push -u origin main
```

## 8. Streamlit Cloud 배포

Streamlit Cloud에서 아래처럼 설정합니다.

```text
Repository: GitHub 저장소 선택
Branch: main
Main file path: app.py
```

이 버전은 `.streamlit/secrets.toml`을 쓰지 않으므로 Secrets 입력은 필요 없습니다.

## 9. Apps Script URL 수정 후 재배포 주의

Apps Script 코드를 수정하면 아래 작업을 다시 해야 합니다.

```text
Apps Script → 배포 → 배포 관리 → 수정 → 새 버전 → 배포
```

기존 URL은 보통 유지됩니다.

## 10. 선택 보안 설정

Apps Script Web App을 `모든 사용자`로 열기 때문에 URL을 아는 사람은 요청할 수 있습니다.
내부 테스트에서는 괜찮지만, 조금 더 안전하게 쓰려면 API Key를 설정할 수 있습니다.

### Apps Script에서 API Key 설정

Apps Script 화면에서:

```text
프로젝트 설정 → 스크립트 속성 → 스크립트 속성 추가
```

아래처럼 추가합니다.

```text
속성: APP_KEY
값: 원하는_긴_문자열
```

### app.py에도 동일하게 입력

```python
DEFAULT_API_KEY = "원하는_긴_문자열"
```

이후 앱을 다시 배포하면 됩니다.
