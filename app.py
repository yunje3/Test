import calendar
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

# =========================================================
# Google Apps Script Web App 설정
# =========================================================
# Streamlit Secrets / .streamlit 폴더를 사용하지 않는 방식입니다.
# 아래 DEFAULT_WEB_APP_URL에 Apps Script 배포 후 받은 웹 앱 URL을 붙여넣으세요.
# 예: https://script.google.com/macros/s/AKfycbxxxxxxxxxxxxxxxxxxxx/exec
DEFAULT_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx6N4JtS_BWyT1tpc2fprATE_BCk0RFPwMhzCH1THysgAHe4V7wyZvtO9ivqS6C2T0/exec"

# Apps Script의 Script Properties에 APP_KEY를 설정한 경우에만 입력하세요.
# 처음 테스트할 때는 비워둬도 됩니다.
DEFAULT_API_KEY = ""

APP_TITLE = "팀 예산 관리 시스템"
SHEET_COLUMNS = [
    "id",
    "date",
    "month",
    "member",
    "category",
    "amount",
    "title",
    "memo",
    "created_at",
]
CATEGORIES = ["수선유지비", "비품", "개량공사"]
MEMBERS = ["부장님", "팀원1", "팀원2", "팀원3", "팀원4"]


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .stApp {
        background: #f7f6f3;
        color: #37352f;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }
    [data-testid="stSidebar"] {
        background: #fbfbfa;
        border-right: 1px solid #e9e5df;
    }
    h1, h2, h3 {
        color: #37352f;
        letter-spacing: -0.03em;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e9e5df;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(15, 15, 15, 0.04);
    }
    .notion-card {
        background: #ffffff;
        border: 1px solid #e9e5df;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(15, 15, 15, 0.04);
        margin-bottom: 14px;
    }
    .small-muted {
        color: #787774;
        font-size: 0.9rem;
    }
    .calendar-head {
        font-weight: 700;
        text-align: center;
        color: #787774;
        padding: 8px 0;
    }
    .calendar-cell {
        min-height: 98px;
        background: #ffffff;
        border: 1px solid #e9e5df;
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 8px;
    }
    .calendar-cell-muted {
        min-height: 98px;
        background: #fafafa;
        border: 1px solid #efefef;
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 8px;
        color: #b0afac;
    }
    .calendar-day {
        font-weight: 700;
        margin-bottom: 8px;
    }
    .calendar-badge {
        display: inline-block;
        background: #f1f1ef;
        border-radius: 999px;
        padding: 2px 8px;
        font-size: 0.75rem;
        margin: 2px 2px 2px 0;
        color: #37352f;
    }
    .amount-text {
        color: #0f7b6c;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .error-box {
        background: #fff4f4;
        border: 1px solid #ffd6d6;
        color: #8a1f1f;
        border-radius: 14px;
        padding: 16px 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# API 유틸
# =========================================================
def get_web_app_url() -> str:
    return DEFAULT_WEB_APP_URL.strip()


def get_api_key() -> str:
    return DEFAULT_API_KEY.strip()


def build_params(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if get_api_key():
        params["api_key"] = get_api_key()
    if extra:
        params.update(extra)
    return params


def ensure_configured() -> bool:
    if not get_web_app_url():
        st.markdown(
            """
            <div class="error-box">
                <b>Apps Script Web App URL이 비어있어.</b><br>
                <code>app.py</code> 파일 상단의 <code>DEFAULT_WEB_APP_URL</code>에 Apps Script 웹 앱 URL을 넣은 뒤 다시 실행해줘.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(
            'DEFAULT_WEB_APP_URL = "https://script.google.com/macros/s/배포_ID/exec"',
            language="python",
        )
        return False
    return True


@st.cache_data(ttl=20, show_spinner=False)
def fetch_records_cached(web_app_url: str, api_key: str) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"action": "list"}
    if api_key:
        params["api_key"] = api_key

    response = requests.get(web_app_url, params=params, timeout=20)
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result.get("message", "Apps Script 응답 오류"))

    return result.get("records", [])


def fetch_records() -> List[Dict[str, Any]]:
    return fetch_records_cached(get_web_app_url(), get_api_key())


def post_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    if get_api_key():
        payload["api_key"] = get_api_key()

    response = requests.post(get_web_app_url(), json=payload, timeout=20)
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result.get("message", "Apps Script 처리 오류"))

    fetch_records_cached.clear()
    return result


def to_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=SHEET_COLUMNS)

    df = pd.DataFrame(records)
    for col in SHEET_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[SHEET_COLUMNS]
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["month"] = df["date"].apply(lambda x: x.strftime("%Y-%m") if pd.notna(x) else "")
    df["created_at"] = df["created_at"].astype(str)
    return df.sort_values(["date", "created_at"], ascending=[False, False]).reset_index(drop=True)


def format_won(value: Any) -> str:
    try:
        return f"{int(value):,}원"
    except Exception:
        return "0원"


# =========================================================
# 화면 컴포넌트
# =========================================================
def render_header() -> None:
    st.title("📊 팀 예산 관리 시스템")
    st.caption("Google Apps Script + Google Sheets 기반 / 노션 스타일 예산 기록")


def render_sidebar() -> None:
    st.sidebar.title("⚙️ 설정 상태")
    if get_web_app_url():
        st.sidebar.success("Apps Script URL 설정됨")
        st.sidebar.caption(get_web_app_url()[:45] + "...")
    else:
        st.sidebar.error("Apps Script URL 미설정")

    if get_api_key():
        st.sidebar.info("API Key 사용 중")
    else:
        st.sidebar.caption("API Key 미사용")

    st.sidebar.divider()
    if st.sidebar.button("🔄 데이터 새로고침", use_container_width=True):
        fetch_records_cached.clear()
        st.rerun()

    st.sidebar.markdown(
        """
        **저장 구조**

        Streamlit → Apps Script → Google Sheets
        """
    )


def render_input_tab(df: pd.DataFrame) -> None:
    left, right = st.columns([0.38, 0.62], gap="large")

    with left:
        st.subheader("📝 내역 입력")
        with st.form("budget_form", clear_on_submit=True):
            used_date = st.date_input("사용일", value=date.today())
            member = st.selectbox("팀원", MEMBERS)
            category = st.selectbox("예산 항목", CATEGORIES)
            title = st.text_input("내용", placeholder="예: 센서 브라켓 구매")
            amount = st.number_input("사용 금액", min_value=0, step=1000, format="%d")
            memo = st.text_area("메모", placeholder="필요하면 상세 내용을 적어줘.", height=90)
            submitted = st.form_submit_button("기록 저장하기", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.warning("사용 금액은 0원보다 커야 해.")
            elif not title.strip():
                st.warning("내용을 입력해줘.")
            else:
                try:
                    post_action(
                        {
                            "action": "add",
                            "record": {
                                "date": used_date.strftime("%Y-%m-%d"),
                                "month": used_date.strftime("%Y-%m"),
                                "member": member,
                                "category": category,
                                "amount": int(amount),
                                "title": title.strip(),
                                "memo": memo.strip(),
                            },
                        }
                    )
                    st.success("저장 완료")
                    st.rerun()
                except Exception as exc:
                    st.error(f"저장 실패: {exc}")

    with right:
        st.subheader("📂 최근 입력 내역")
        if df.empty:
            st.info("아직 등록된 데이터가 없어.")
            return

        display_df = df.copy()
        display_df["amount"] = display_df["amount"].map(format_won)
        display_df = display_df[["date", "member", "category", "title", "amount", "memo"]]
        display_df.columns = ["사용일", "팀원", "항목", "내용", "금액", "메모"]
        st.dataframe(display_df.head(30), use_container_width=True, hide_index=True)

        st.divider()
        with st.expander("기록 삭제"):
            options = [
                f"{row.id} | {row.date} | {row.member} | {row.category} | {row.title} | {format_won(row.amount)}"
                for row in df.itertuples()
            ]
            selected = st.selectbox("삭제할 기록", options=options)
            if st.button("선택 기록 삭제", type="secondary"):
                try:
                    record_id = selected.split(" | ")[0]
                    post_action({"action": "delete", "id": record_id})
                    st.success("삭제 완료")
                    st.rerun()
                except Exception as exc:
                    st.error(f"삭제 실패: {exc}")

        with st.expander("위험 작업"):
            st.warning("전체 초기화는 되돌릴 수 없어.")
            confirm_text = st.text_input("초기화하려면 DELETE 입력")
            if st.button("전체 데이터 초기화"):
                if confirm_text == "DELETE":
                    try:
                        post_action({"action": "clear"})
                        st.success("전체 데이터 초기화 완료")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"초기화 실패: {exc}")
                else:
                    st.error("DELETE를 정확히 입력해야 해.")


def render_dashboard_tab(df: pd.DataFrame) -> None:
    st.subheader("📈 전체 대시보드")

    if df.empty:
        st.info("대시보드를 표시할 데이터가 없어.")
        return

    total_amount = int(df["amount"].sum())
    count = len(df)
    top_category = (
        df.groupby("category")["amount"].sum().sort_values(ascending=False).index[0]
    )
    top_category_amount = int(
        df.groupby("category")["amount"].sum().sort_values(ascending=False).iloc[0]
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("전체 누적 사용액", format_won(total_amount))
    col2.metric("최대 사용 항목", f"{top_category} / {format_won(top_category_amount)}")
    col3.metric("데이터 건수", f"{count:,}건")

    chart_left, chart_right = st.columns(2, gap="large")

    with chart_left:
        st.markdown("### 🏷️ 항목별 예산 분포")
        category_df = df.groupby("category", as_index=False)["amount"].sum()
        st.bar_chart(category_df, x="category", y="amount", use_container_width=True)

    with chart_right:
        st.markdown("### 👥 팀원별 누적 사용액")
        member_df = df.groupby("member", as_index=False)["amount"].sum()
        st.bar_chart(member_df, x="member", y="amount", use_container_width=True)

    st.markdown("### 📅 월별 / 항목별 요약")
    summary = pd.pivot_table(
        df,
        index="month",
        columns="category",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )
    for category in CATEGORIES:
        if category not in summary.columns:
            summary[category] = 0
    summary = summary[CATEGORIES]
    summary["합계"] = summary.sum(axis=1)
    summary = summary.sort_index(ascending=False).reset_index()
    money_cols = CATEGORIES + ["합계"]
    for col in money_cols:
        summary[col] = summary[col].map(format_won)
    st.dataframe(summary, use_container_width=True, hide_index=True)


def render_calendar_cell(day: int, current_month: str, day_df: pd.DataFrame) -> str:
    if day == 0:
        return '<div class="calendar-cell-muted"></div>'

    date_text = f"{current_month}-{day:02d}"
    if day_df.empty:
        return f"""
        <div class="calendar-cell">
            <div class="calendar-day">{day}</div>
            <span class="small-muted">기록 없음</span>
        </div>
        """

    total = int(day_df["amount"].sum())
    badges = "".join(
        [
            f'<span class="calendar-badge">{row.category}</span>'
            for row in day_df.head(3).itertuples()
        ]
    )
    more = "" if len(day_df) <= 3 else f'<span class="calendar-badge">+{len(day_df) - 3}</span>'

    return f"""
    <div class="calendar-cell">
        <div class="calendar-day">{day}</div>
        <div class="amount-text">{format_won(total)}</div>
        <div>{badges}{more}</div>
    </div>
    """


def render_calendar_tab(df: pd.DataFrame) -> None:
    st.subheader("🗓️ 캘린더")

    if df.empty:
        st.info("캘린더에 표시할 데이터가 없어.")
        return

    today = date.today()
    available_months = sorted(df["month"].dropna().unique().tolist(), reverse=True)
    default_month = today.strftime("%Y-%m")
    if default_month not in available_months and available_months:
        default_month = available_months[0]

    selected_month = st.selectbox(
        "조회 월",
        options=available_months,
        index=available_months.index(default_month) if default_month in available_months else 0,
    )

    year, month = map(int, selected_month.split("-"))
    month_df = df[df["month"] == selected_month].copy()

    st.markdown(
        f"<div class='notion-card'><b>{year}년 {month}월</b> 사용금액: <b>{format_won(month_df['amount'].sum())}</b> / 기록 {len(month_df)}건</div>",
        unsafe_allow_html=True,
    )

    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    cols = st.columns(7)
    for idx, name in enumerate(day_names):
        cols[idx].markdown(f"<div class='calendar-head'>{name}</div>", unsafe_allow_html=True)

    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdayscalendar(year, month):
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].markdown(render_calendar_cell(0, selected_month, pd.DataFrame()), unsafe_allow_html=True)
                continue

            day_date = date(year, month, day)
            day_df = month_df[month_df["date"] == day_date]
            cols[idx].markdown(render_calendar_cell(day, selected_month, day_df), unsafe_allow_html=True)

    st.divider()
    selected_day = st.date_input("상세 조회 날짜", value=date(year, month, 1))
    detail_df = df[df["date"] == selected_day]
    st.markdown(f"### {selected_day.strftime('%Y-%m-%d')} 상세 기록")
    if detail_df.empty:
        st.caption("해당 날짜 기록이 없어.")
    else:
        show_df = detail_df[["member", "category", "title", "amount", "memo"]].copy()
        show_df["amount"] = show_df["amount"].map(format_won)
        show_df.columns = ["팀원", "항목", "내용", "금액", "메모"]
        st.dataframe(show_df, use_container_width=True, hide_index=True)


def render_raw_data_tab(df: pd.DataFrame) -> None:
    st.subheader("🧾 전체 데이터")
    if df.empty:
        st.info("데이터가 없어.")
        return

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "CSV 다운로드",
        data=csv,
        file_name=f"budget_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


# =========================================================
# Main
# =========================================================
def main() -> None:
    render_header()
    render_sidebar()

    if not ensure_configured():
        st.stop()

    try:
        records = fetch_records()
        df = to_dataframe(records)
    except Exception as exc:
        st.error("Apps Script / Google Sheets 연결에 실패했어.")
        st.exception(exc)
        st.stop()

    tabs = st.tabs(["입력", "대시보드", "캘린더", "전체 데이터"])
    with tabs[0]:
        render_input_tab(df)
    with tabs[1]:
        render_dashboard_tab(df)
    with tabs[2]:
        render_calendar_tab(df)
    with tabs[3]:
        render_raw_data_tab(df)


if __name__ == "__main__":
    main()
