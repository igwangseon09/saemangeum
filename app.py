import io
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="군산 새만금단지 입주기업 분석", layout="wide")

st.title("군산 새만금단지 9개 공구별 · 연도별 입주기업 분석")
st.caption("CSV를 업로드하거나 샘플 데이터를 사용해 공구별/연도별 입주 기업 수를 집계합니다.")

@st.cache_data
def load_sample():
    return pd.read_csv("sample_data.csv")

def validate_columns(df: pd.DataFrame):
    required = {"공구", "입주연도", "업체명"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"다음 컬럼이 필요합니다: {', '.join(missing)}")
        return False
    # 타입 정리
    try:
        df["입주연도"] = pd.to_numeric(df["입주연도"], errors="coerce").astype("Int64")
    except Exception:
        st.error("`입주연도`는 숫자여야 합니다.")
        return False
    df["공구"] = df["공구"].astype(str)
    df["업체명"] = df["업체명"].astype(str)
    return True

with st.sidebar:
    st.header("데이터 입력")
    uploaded = st.file_uploader("CSV 업로드 (공구, 입주연도, 업체명)", type=["csv"])
    use_sample = st.checkbox("샘플 데이터 사용", value=not bool(uploaded))

    if use_sample:
        df = load_sample()
    else:
        if uploaded is not None:
            df = pd.read_csv(uploaded)
        else:
            df = None

    if df is not None and validate_columns(df):
        st.success("데이터 로드 완료")
    elif df is not None:
        st.stop()
    else:
        st.info("좌측에서 CSV를 업로드하거나 샘플 데이터를 선택하세요.")
        st.stop()

# 필터
with st.expander("🔍 필터", expanded=True):
    all_gonggu = sorted(df["공구"].dropna().unique().tolist())
    sel_gonggu = st.multiselect("공구 선택", options=all_gonggu, default=all_gonggu)
    min_year, max_year = int(df["입주연도"].min()), int(df["입주연도"].max())
    year_range = st.slider("연도 범위", min_value=min_year, max_value=max_year, value=(min_year, max_year), step=1)
    text_query = st.text_input("업체명 검색(포함 일치)", "")

# 필터 적용
mask = df["공구"].isin(sel_gonggu) & df["입주연도"].between(year_range[0], year_range[1])
if text_query.strip():
    mask = mask & df["업체명"].str.contains(text_query.strip(), case=False, na=False)

fdf = df[mask].copy()

# 집계: 연도별 입주 기업 수 (행: 연도, 값: 건수)
yearly = (
    fdf.groupby(["입주연도"])
    .agg(입주기업수=("업체명", "count"))
    .reset_index()
    .sort_values("입주연도")
)

left, right = st.columns([1.1,1])
with left:
    st.subheader("연도별 입주 기업 수")
    if not yearly.empty:
        chart = (
            alt.Chart(yearly)
            .mark_bar()
            .encode(
                x=alt.X("입주연도:O", title="연도", sort=None),
                y=alt.Y("입주기업수:Q", title="기업 수"),
                tooltip=["입주연도", "입주기업수"]
            )
            .properties(height=380)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("해당 조건에 맞는 데이터가 없습니다.")

with right:
    st.subheader("요약")
    st.metric("표시 중인 공구 수", len(sel_gonggu))
    st.metric("표시 중 연도 범위", f"{year_range[0]}–{year_range[1]}")
    st.metric("표시 중 총 기업 수", int(fdf.shape[0]))

st.divider()

# 피벗 테이블: (행)공구 × (열)입주연도 → count
st.subheader("피벗테이블 (공구 × 연도)")
pivot = pd.pivot_table(
    fdf,
    index="공구",
    columns="입주연도",
    values="업체명",
    aggfunc="count",
    fill_value=0,
).sort_index()
st.dataframe(pivot, use_container_width=True)

# 다운로드
st.subheader("다운로드")
col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "집계 결과(CSV) 다운로드 - 연도별 합계",
        data=yearly.to_csv(index=False).encode("utf-8-sig"),
        file_name="yearly_counts.csv",
        mime="text/csv",
    )
with col2:
    # 피벗 테이블 다운로드
    csv_bytes = pivot.reset_index().to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "피벗테이블(CSV) 다운로드 - 공구×연도",
        data=csv_bytes,
        file_name="pivot_counts.csv",
        mime="text/csv",
    )

st.caption("Tip: 원본 데이터는 한 행이 한 기업의 '입주'를 의미합니다. 동일 기업이 여러 연도/공구에 있으면 각 행이 별도로 집계됩니다.")
