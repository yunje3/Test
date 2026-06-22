import calendar
import os
import uuid
from datetime import date, datetime
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="팀 예산 관리 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

HEADERS = [
    "id",
    "used_date",
    "month",
    "member",
    "category",
    "amount",
    "title",
    "memo",
    "created_at",
    "updated_at",
]

MEMBERS = ["부장님", "팀원1", "팀원2", "팀원3", "팀원4"]
CATEGORIES = ["수선유지비", "비품", "개량공사"]

# Streamlit Cloud에서 Secrets를 쓰지 않고 바로 실행하고 싶으면 아래에 Apps Script Web App URL을 직접 넣어도 된다.
# 단, GitHub 공개 저장소라면 URL이 노출되므로 Streamlit Cloud의 Secrets 사용을 권장한다.
DEFAULT_WEB_APP_URL = ""
DEFAULT_API_KEY = ""

CATEGORY_EMOJI = {
    "수선유지비": "🛠️",
    "비품": "📦",
    "개량공사": "🏗️",
}


st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        .notion-title {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
        }
        .notion-subtitle {
            color: #6b7280;
            font-size: 0.98rem;
            margin-bottom: 1.4rem;
        }
        .notion-card {
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            padding: 1.1rem 1.2rem;
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .mini-label {
            color: #6b7280;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .mini-value {
            font-size: 1.45rem;
            font-weight: 800;
            letter-spacing: -0.04em;
        }
        .calendar-header {
            text-align: center;
            color: #6b7280;
            font-weight: 800;
            font-size: 0.82rem;
            padding: 0.4rem 0;
        }
        .day-detail-card {
            border-left: 4px solid #111827;
            background: #f9fafb;
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
            margin-bottom: 0.65rem;
        }
        .small-muted { color: #6b7280; font-size: 0.86rem; }
        div[data-testid="stMetric"] {
            border: 1px solid #e5e7eb;
            background: #ffffff;
            padding: 1rem;
            border-radius: 16px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Apps Script API 연결
# -----------------------------
def get_apps_script_config() -> Dict[str, str]:
    """Streamlit Cloud Secrets, 환경변수, 기본값 순서로 Apps Script 연결 정보를 읽는다.

    Streamlit Cloud에 Secrets가 아직 없거나 로컬에 .streamlit/secrets.toml이 없어도
    앱이 바로 죽지 않도록 예외를 무시하고 안내 화면으로 넘어가게 한다.
    """
    apps_script_secrets: Dict[str, Any] = {}

    try:
        # Streamlit Cloud에서는 App settings > Secrets 값이 여기로 들어온다.
        # 로컬에서는 .streamlit/secrets.toml 값이 여기로 들어온다.
        apps_script_secrets = dict(st.secrets.get("apps_script", {}))
    except Exception:
        # secrets.toml이 없으면 FileNotFoundError가 날 수 있다.
        # 이 경우 환경변수 또는 DEFAULT_WEB_APP_URL을 사용한다.
        apps_script_secrets = {}

    web_app_url = (
        apps_script_secrets.get("web_app_url")
        or os.getenv("APPS_SCRIPT_WEB_APP_URL", "")
        or DEFAULT_WEB_APP_URL
    )
    api_key = (
        apps_script_secrets.get("api_key")
        or os.getenv("APPS_SCRIPT_API_KEY", "")
        or DEFAULT_API_KEY
    )

    return {
        "web_app_url": str(web_app_url).strip(),
        "api_key": str(api_key).strip(),
    }


def show_setup_error_if_needed():
    """Apps Script URL이 없으면 설정 안내를 표시하고 앱을 중단한다."""
    config = get_apps_script_config()
    if config["web_app_url"]:
        return

    st.error("Apps Script Web App URL이 설정되지 않았어.")
    st.info("GitHub에는 .streamlit 폴더를 올리지 않아도 돼. Streamlit Cloud의 Secrets에 값을 넣으면 돼.")
    st.markdown(
        """
        ### Streamlit Cloud에서 설정하는 방법

        1. Streamlit Cloud 앱 화면에서 **Manage app** 클릭
        2. **Settings** 클릭
        3. **Secrets** 메뉴 열기
        4. 아래 내용을 붙여넣기
        5. **Save** 후 앱 재부팅

        ```toml
        [apps_script]
        web_app_url = "https://script.google.com/macros/s/배포_ID/exec"
        api_key = ""
        ```

        ### Secrets를 아예 쓰기 싫을 때

        `app.py` 상단의 `DEFAULT_WEB_APP_URL` 값에 Apps Script Web App URL을 직접 넣어도 된다.
        단, GitHub 공개 저장소라면 URL이 노출된다.
        """
    )
    st.stop()


def call_apps_script(action: str, **kwargs) -> Dict[str, Any]:
    """Apps Script Web App에 요청을 보내고 JSON 응답을 반환한다."""
    config = get_apps_script_config()
    payload: Dict[str, Any] = {
        "action": action,
        **kwargs,
    }

    if config["api_key"]:
        payload["api_key"] = config["api_key"]

    try:
        response = requests.post(
            config["web_app_url"],
            json=payload,
            timeout=30,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Apps Script 서버 요청 실패: {error}") from error

    try:
        data = response.json()
    except ValueError as error:
        preview = response.text[:500]
        raise RuntimeError(f"Apps Script 응답이 JSON이 아니야: {preview}") from error

    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "Apps Script 처리 실패")

    return data


def fetch_records() -> List[Dict[str, Any]]:
    """Google Sheet에 저장된 예산 기록 목록을 가져온다."""
    data = call_apps_script("list")
    return data.get("records", [])


def append_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """새 예산 기록을 Apps Script를 통해 Google Sheet에 추가한다."""
    return call_apps_script("add", record=record)


def delete_record(record_id: str) -> bool:
    """id가 일치하는 예산 기록을 삭제한다."""
    data = call_apps_script("delete", id=record_id)
    return bool(data.get("deleted"))


def clear_all_records() -> None:
    """헤더를 제외한 모든 예산 기록을 삭제한다."""
    call_apps_script("clear")


def records_to_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Apps Script 응답 데이터를 DataFrame으로 변환한다."""
    if not records:
        return empty_dataframe()

    normalized_records = []
    for record in records:
        normalized = {header: record.get(header, "") for header in HEADERS}
        normalized_records.append(normalized)

    df = pd.DataFrame(normalized_records, columns=HEADERS)
    df = df[df["id"].astype(str).str.strip() != ""]

    if df.empty:
        return empty_dataframe()

    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )

    df["used_date"] = pd.to_datetime(df["used_date"], errors="coerce")
    df = df.dropna(subset=["used_date"])

    if df.empty:
        return empty_dataframe()

    df["used_date_only"] = df["used_date"].dt.date
    df["month"] = df["used_date"].dt.strftime("%Y-%m")

    return df.sort_values("used_date", ascending=False).reset_index(drop=True)


def empty_dataframe() -> pd.DataFrame:
    df = pd.DataFrame(columns=HEADERS + ["used_date_only"])
    df["amount"] = pd.Series(dtype="int")
    return df


# -----------------------------
# 공통 표시 함수
# -----------------------------
def format_won(value) -> str:
    try:
        return f"{int(value):,}원"
    except Exception:
        return "0원"


def show_header():
    st.markdown('<div class="notion-title">📊 팀 예산 관리 시스템</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="notion-subtitle">Apps Script를 API 서버로 사용하고 Google Sheets에 데이터를 저장하는 Streamlit 예산 취합/캘린더/대시보드</div>',
        unsafe_allow_html=True,
    )


def show_connection_card():
    config = get_apps_script_config()
    with st.sidebar:
        st.markdown("### ⚙️ 연결 정보")
        st.caption("데이터 저장소")
        st.code("Google Sheets\nvia Apps Script Web App", language="text")
        st.caption("Apps Script URL")
        st.code(config["web_app_url"][:80] + ("..." if len(config["web_app_url"]) > 80 else ""), language="text")
        if config["api_key"]:
            st.success("API Key 사용 중")
        else:
            st.warning("API Key 미사용: 사내/개인 용도라도 공개 URL 관리에 주의해줘.")
        st.caption("Streamlit secrets에는 Web App URL과 선택 API Key만 넣으면 돼.")


def load_dataframe_or_stop() -> pd.DataFrame:
    """기록 데이터를 로드하고, 실패 시 안내를 표시한다."""
    try:
        return records_to_dataframe(fetch_records())
    except Exception as error:
        st.error("Apps Script / Google Sheets 연결에 실패했어.")
        st.exception(error)
        st.stop()


# -----------------------------
# 입력 탭
# -----------------------------
def render_input_tab(df: pd.DataFrame):
    left, right = st.columns([0.95, 1.55], gap="large")

    with left:
        st.markdown("### 📝 내역 입력")
        with st.form("budget_form", clear_on_submit=True):
            used_date = st.date_input("사용일", value=date.today())
            member = st.selectbox("팀원", MEMBERS)
            category = st.selectbox("예산 항목", CATEGORIES, format_func=lambda x: f"{CATEGORY_EMOJI.get(x, '📌')} {x}")
            amount = st.number_input("사용 금액", min_value=0, step=1000, format="%d")
            title = st.text_input("내용", placeholder="예: 리미트 센서 교체, 공구 구매")
            memo = st.text_area("메모", placeholder="필요하면 상세 내용을 적어줘", height=100)

            submitted = st.form_submit_button("기록 저장하기", type="primary", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.warning("사용 금액은 0원보다 커야 해.")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record = {
                    "id": uuid.uuid4().hex[:12],
                    "used_date": used_date.isoformat(),
                    "month": used_date.strftime("%Y-%m"),
                    "member": member,
                    "category": category,
                    "amount": int(amount),
                    "title": title.strip(),
                    "memo": memo.strip(),
                    "created_at": now,
                    "updated_at": now,
                }
                try:
                    append_record(record)
                    st.success("Google Sheets에 기록했어.")
                    st.rerun()
                except Exception as error:
                    st.error("기록 저장에 실패했어.")
                    st.exception(error)

    with right:
        st.markdown("### 📂 최근 입력 내역")
        if df.empty:
            st.info("아직 등록된 데이터가 없어.")
        else:
            recent = df.head(10).copy()
            recent["사용일"] = recent["used_date"].dt.strftime("%Y-%m-%d")
            recent["금액"] = recent["amount"].map(format_won)
            recent["항목"] = recent["category"].map(lambda x: f"{CATEGORY_EMOJI.get(x, '📌')} {x}")
            st.dataframe(
                recent[["사용일", "member", "항목", "title", "금액", "memo"]].rename(
                    columns={"member": "팀원", "title": "내용", "memo": "메모"}
                ),
                use_container_width=True,
                hide_index=True,
            )


# -----------------------------
# 캘린더 탭
# -----------------------------
def render_calendar_tab(df: pd.DataFrame):
    st.markdown("### 📅 예산 캘린더")

    if "selected_calendar_date" not in st.session_state:
        st.session_state.selected_calendar_date = date.today()

    control_left, control_right = st.columns([0.3, 0.7])
    with control_left:
        base_date = st.date_input("조회 월", value=st.session_state.selected_calendar_date, key="calendar_base_date")
    selected_year = base_date.year
    selected_month = base_date.month

    month_df = df[
        (df["used_date"].dt.year == selected_year)
        & (df["used_date"].dt.month == selected_month)
    ].copy() if not df.empty else empty_dataframe()

    with control_right:
        month_total = month_df["amount"].sum() if not month_df.empty else 0
        month_count = len(month_df)
        st.markdown(
            f"""
            <div class="notion-card">
                <div class="mini-label">{selected_year}년 {selected_month}월 요약</div>
                <div class="mini-value">{format_won(month_total)} · {month_count}건</div>
                <div class="small-muted">날짜 버튼을 누르면 오른쪽 상세 기록이 바뀐다.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    day_amount_map = {}
    day_count_map = {}
    if not month_df.empty:
        day_group = month_df.groupby(month_df["used_date"].dt.day).agg(total=("amount", "sum"), count=("id", "count"))
        day_amount_map = day_group["total"].to_dict()
        day_count_map = day_group["count"].to_dict()

    cal_left, cal_right = st.columns([1.5, 1], gap="large")

    with cal_left:
        week_names = ["일", "월", "화", "수", "목", "금", "토"]
        header_cols = st.columns(7)
        for col, name in zip(header_cols, week_names):
            col.markdown(f'<div class="calendar-header">{name}</div>', unsafe_allow_html=True)

        cal = calendar.Calendar(firstweekday=6)
        for week in cal.monthdatescalendar(selected_year, selected_month):
            cols = st.columns(7)
            for col, current_day in zip(cols, week):
                if current_day.month != selected_month:
                    col.markdown(" ")
                    continue

                total = day_amount_map.get(current_day.day, 0)
                count = day_count_map.get(current_day.day, 0)
                label = f"{current_day.day}일"
                if count:
                    label += f"\n{format_won(total)}\n{count}건"
                else:
                    label += "\n-"

                if col.button(label, key=f"calendar_day_{current_day.isoformat()}", use_container_width=True):
                    st.session_state.selected_calendar_date = current_day
                    st.rerun()

    with cal_right:
        selected_day = st.session_state.selected_calendar_date
        st.markdown(f"### 🗓️ {selected_day.strftime('%Y-%m-%d')} 기록")

        if df.empty:
            day_records = empty_dataframe()
        else:
            day_records = df[df["used_date_only"] == selected_day].copy()

        if day_records.empty:
            st.info("선택한 날짜에 기록이 없어.")
        else:
            st.metric("일 합계", format_won(day_records["amount"].sum()), f"{len(day_records)}건")
            for _, row in day_records.sort_values("amount", ascending=False).iterrows():
                title = row["title"] if row["title"] else "내용 없음"
                memo = row["memo"] if row["memo"] else "-"
                st.markdown(
                    f"""
                    <div class="day-detail-card">
                        <b>{CATEGORY_EMOJI.get(row['category'], '📌')} {row['category']}</b> · {row['member']}<br>
                        <span class="small-muted">{title}</span><br>
                        <b>{format_won(row['amount'])}</b><br>
                        <span class="small-muted">{memo}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# -----------------------------
# 대시보드 탭
# -----------------------------
def render_dashboard_tab(df: pd.DataFrame):
    st.markdown("### 📊 전체 대시보드")

    if df.empty:
        st.info("대시보드를 표시할 데이터가 없어.")
        return

    current_month = date.today().strftime("%Y-%m")
    current_month_df = df[df["month"] == current_month]

    cat_map = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    member_map = df.groupby("member")["amount"].sum().sort_values(ascending=False)
    top_category = cat_map.index[0] if not cat_map.empty else "-"

    metric_cols = st.columns(4)
    metric_cols[0].metric("전체 누적 사용액", format_won(df["amount"].sum()))
    metric_cols[1].metric("이번 달 사용액", format_won(current_month_df["amount"].sum()))
    metric_cols[2].metric("최대 사용 항목", top_category, format_won(cat_map.iloc[0]) if not cat_map.empty else "0원")
    metric_cols[3].metric("데이터 건수", f"{len(df)}건")

    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        st.markdown("#### 항목별 예산 분포")
        st.bar_chart(cat_map)

    with chart_right:
        st.markdown("#### 팀원별 누적 사용액")
        st.bar_chart(member_map)

    st.markdown("#### 월별/항목별 요약")
    pivot = pd.pivot_table(
        df,
        index="month",
        columns="category",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    ).sort_index(ascending=False)

    for category in CATEGORIES:
        if category not in pivot.columns:
            pivot[category] = 0
    pivot = pivot[CATEGORIES]
    pivot["합계"] = pivot.sum(axis=1)

    display_pivot = pivot.copy()
    for col in display_pivot.columns:
        display_pivot[col] = display_pivot[col].map(format_won)

    st.dataframe(display_pivot, use_container_width=True)


# -----------------------------
# 기록 관리 탭
# -----------------------------
def render_records_tab(df: pd.DataFrame):
    st.markdown("### 🗃️ 기록 관리")

    if df.empty:
        st.info("관리할 기록이 없어.")
        return

    display_df = df.copy()
    display_df["사용일"] = display_df["used_date"].dt.strftime("%Y-%m-%d")
    display_df["금액"] = display_df["amount"].map(format_won)
    display_df["항목"] = display_df["category"].map(lambda x: f"{CATEGORY_EMOJI.get(x, '📌')} {x}")
    display_df["삭제표시"] = display_df.apply(
        lambda row: f"{row['used_date'].strftime('%Y-%m-%d')} | {row['member']} | {row['category']} | {format_won(row['amount'])} | {row['title'] or '-'}",
        axis=1,
    )

    st.dataframe(
        display_df[["사용일", "member", "항목", "title", "금액", "memo", "created_at"]].rename(
            columns={"member": "팀원", "title": "내용", "memo": "메모", "created_at": "생성일"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.markdown("#### 삭제")
    selected_label = st.selectbox("삭제할 기록", display_df["삭제표시"].tolist())
    selected_id = display_df.loc[display_df["삭제표시"] == selected_label, "id"].iloc[0]

    col_a, col_b = st.columns([0.25, 0.75])
    with col_a:
        if st.button("선택 기록 삭제", type="secondary", use_container_width=True):
            try:
                if delete_record(selected_id):
                    st.success("선택한 기록을 삭제했어.")
                    st.rerun()
                else:
                    st.error("삭제할 기록을 찾지 못했어. 새로고침 후 다시 시도해줘.")
            except Exception as error:
                st.error("기록 삭제에 실패했어.")
                st.exception(error)

    with col_b:
        with st.expander("전체 데이터 초기화"):
            st.warning("Google Sheets의 모든 예산 기록이 삭제되고 헤더만 남아. 되돌릴 수 없어.")
            confirm = st.text_input("초기화하려면 DELETE를 입력", key="delete_all_confirm")
            if st.button("전체 초기화 실행", disabled=(confirm != "DELETE")):
                try:
                    clear_all_records()
                    st.success("전체 데이터를 초기화했어.")
                    st.rerun()
                except Exception as error:
                    st.error("전체 초기화에 실패했어.")
                    st.exception(error)


# -----------------------------
# 메인
# -----------------------------
def main():
    show_header()
    show_setup_error_if_needed()
    show_connection_card()
    df = load_dataframe_or_stop()

    tab_input, tab_calendar, tab_dashboard, tab_records = st.tabs(
        ["📝 데이터 입력", "📅 캘린더", "📊 전체 대시보드", "🗃️ 기록 관리"]
    )

    with tab_input:
        render_input_tab(df)
    with tab_calendar:
        render_calendar_tab(df)
    with tab_dashboard:
        render_dashboard_tab(df)
    with tab_records:
        render_records_tab(df)


if __name__ == "__main__":
    main()
