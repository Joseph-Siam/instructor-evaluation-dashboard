"""Streamlit instructor-evaluation dashboard (public portfolio demo).

Uses fictional/synthetic class evaluation records for 2021–2024.
All names, scores, and enrollments in the public demo are fabricated.
Run with: python -m streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_FILE = Path(__file__).resolve().parent / "sample_instructor_evaluations.csv"
SCORE_COLUMNS = ["Teaching_Skill_Eval", "Material_Eval", "Human_Skill_Eval"]
SCORE_OPTIONS = {
    "Overall Score": "Overall_Score",
    "Teaching Skill": "Teaching_Skill_Eval",
    "Material Evaluation": "Material_Eval",
    "Human Skill": "Human_Skill_Eval",
}
SCORE_LABELS = {
    "Teaching_Skill_Eval": "Teaching skill",
    "Material_Eval": "Course material",
    "Human_Skill_Eval": "Human skill",
}
DEPARTMENT_COLORS = {"BBA": "#2563EB", "CS": "#F97316"}
REQUIRED_COLUMNS = [
    "Year", "Semester", "Instructor_Name", "Department", "Subject_ID",
    "Sec", "Respondent_No", "Enrollment_No", *SCORE_COLUMNS,
]

st.set_page_config(
    page_title="Instructor Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_dataset(file_path: str) -> pd.DataFrame:
    """Load and validate synthetic demonstration records."""
    data = pd.read_csv(file_path)
    missing = sorted(set(REQUIRED_COLUMNS).difference(data.columns))
    if missing:
        raise ValueError(f"Required Excel columns are missing: {', '.join(missing)}")

    numeric_cols = ["Year", "Semester", "Respondent_No", "Enrollment_No", *SCORE_COLUMNS]
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=REQUIRED_COLUMNS).copy()
    data = data[
        (data["Enrollment_No"] > 0)
        & (data["Respondent_No"] >= 0)
        & (data["Respondent_No"] <= data["Enrollment_No"])
    ].copy()
    data["Year"] = data["Year"].astype(int)
    data["Semester"] = data["Semester"].astype(int)
    data["Department"] = data["Department"].astype(str).str.strip()
    data["Instructor_Name"] = data["Instructor_Name"].astype(str).str.strip()
    data["Overall_Score"] = data[SCORE_COLUMNS].mean(axis=1)
    data["Response_Rate"] = 100 * data["Respondent_No"] / data["Enrollment_No"]
    return data


def chart_style(fig, *, min_y=0, max_y=5, ylabel="Average score / 5"):
    fig.update_layout(
        template="plotly_white",
        height=330,
        margin=dict(l=15, r=15, t=45, b=20),
        legend_title_text="",
        font=dict(family="Arial", size=12),
        hovermode="closest",
    )
    fig.update_yaxes(range=[min_y, max_y], title=ylabel, gridcolor="#E9EEF4")
    return fig


try:
    source = load_dataset(str(DATA_FILE))
except FileNotFoundError:
    st.error("Could not find sample_instructor_evaluations.csv. Put it in the same folder as app.py.")
    st.stop()
except (ValueError, ImportError) as exc:
    st.error(f"Unable to load the dataset: {exc}")
    st.stop()

st.title("Lecturer Evaluation Dashboard")
st.caption("Interactive evaluation analytics  |  Synthetic demonstration data  |  2021–2024")
st.markdown(
    "Compare **Computer Science (CS)** and **Business Administration (BBA)** "
    "using fictional instructor evaluation scores and class-section response rates."
)
st.info("Portfolio demo: All instructor names and evaluation records are synthetic. No real student or instructor data is published.")

# Form controls: the page is recomputed only after the user clicks Apply filters.
st.sidebar.header("Interactive filters")
with st.sidebar.form("evaluation_filters"):
    years_available = sorted(source["Year"].unique().tolist())
    depts_available = sorted(source["Department"].unique().tolist())
    semesters_available = sorted(source["Semester"].unique().tolist())

    selected_years = st.multiselect("Academic year", years_available, default=years_available)
    selected_depts = st.multiselect("Department", depts_available, default=depts_available)
    selected_semesters = st.multiselect(
        "Semester", semesters_available, default=semesters_available
    )
    selected_instructor = st.selectbox(
        "Instructor", ["All instructors", *sorted(source["Instructor_Name"].unique().tolist())]
    )
    selected_metric_name = st.selectbox("Evaluation measure", list(SCORE_OPTIONS))
    minimum_enrollment = st.slider(
        "Minimum enrollment per section", min_value=0, max_value=50, value=0, step=5
    )
    submitted = st.form_submit_button("Apply filters", type="primary", use_container_width=True)

st.sidebar.caption("Change any controls, then select **Apply filters**.")
if not (selected_years and selected_depts and selected_semesters):
    st.warning("Select at least one year, department, and semester in the sidebar.")
    st.stop()

filtered = source.loc[
    source["Year"].isin(selected_years)
    & source["Department"].isin(selected_depts)
    & source["Semester"].isin(selected_semesters)
    & (source["Enrollment_No"] >= minimum_enrollment)
].copy()
if selected_instructor != "All instructors":
    filtered = filtered.loc[filtered["Instructor_Name"] == selected_instructor]

if filtered.empty:
    st.warning("No records match those filters. Broaden the selections in the sidebar.")
    st.stop()

metric_col = SCORE_OPTIONS[selected_metric_name]
metric_label = "Overall score" if metric_col == "Overall_Score" else SCORE_LABELS[metric_col]
respondents = int(filtered["Respondent_No"].sum())
enrollment = int(filtered["Enrollment_No"].sum())
overall_response_rate = 100 * respondents / enrollment if enrollment else 0

# Headline KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Average evaluation", f"{filtered[metric_col].mean():.2f} / 5")
k2.metric("Student response rate", f"{overall_response_rate:.1f}%")
k3.metric("Class sections", f"{len(filtered):,}")
k4.metric("Unique instructors", f"{filtered['Instructor_Name'].nunique():,}")
st.caption(
    "Evaluation scores are averaged across the selected class sections. "
    "Response rate = total respondents ÷ total enrollment × 100."
)

st.divider()
dashboard_tab, instructor_tab, data_tab = st.tabs(
    ["📊 Dashboard", "👩‍🏫 Instructor explorer", "🗂️ Data and methods"]
)

with dashboard_tab:
    left_top, right_top = st.columns(2, gap="large")
    left_bottom, right_bottom = st.columns(2, gap="large")

    # Chart 1: overall department performance
    dep_score = (
        filtered.groupby("Department", as_index=False)[metric_col]
        .mean()
        .rename(columns={metric_col: "Score"})
    )
    fig1 = px.bar(
        dep_score,
        x="Department", y="Score", color="Department",
        color_discrete_map=DEPARTMENT_COLORS,
        text="Score", title=f"Overall department performance: {metric_label}",
    )
    fig1.update_traces(texttemplate="%{y:.2f}", textposition="outside")
    fig1 = chart_style(fig1)
    fig1.update_layout(showlegend=False)
    with left_top:
        st.plotly_chart(fig1, width="stretch")

    # Chart 2: yearly evaluation trend
    yearly = (
        filtered.groupby(["Year", "Department"], as_index=False)[metric_col]
        .mean()
        .rename(columns={metric_col: "Score"})
    )
    fig2 = px.line(
        yearly, x="Year", y="Score", color="Department", markers=True,
        color_discrete_map=DEPARTMENT_COLORS,
        title=f"Yearly evaluation trend: {metric_label}",
    )
    fig2.update_traces(line_width=3, marker_size=9)
    fig2 = chart_style(fig2)
    fig2.update_xaxes(dtick=1, tickformat="d")
    with right_top:
        st.plotly_chart(fig2, width="stretch")

    # Chart 3: three evaluation categories by department
    long_scores = filtered.melt(
        id_vars=["Department"],
        value_vars=SCORE_COLUMNS,
        var_name="Category", value_name="Score",
    )
    long_scores["Category"] = long_scores["Category"].map(SCORE_LABELS)
    category_scores = (
        long_scores.groupby(["Category", "Department"], as_index=False)["Score"].mean()
    )
    fig3 = px.bar(
        category_scores,
        x="Category", y="Score", color="Department", barmode="group",
        color_discrete_map=DEPARTMENT_COLORS,
        category_orders={"Category": list(SCORE_LABELS.values())},
        title="Evaluation category comparison", text="Score",
    )
    fig3.update_traces(texttemplate="%{y:.2f}", textposition="outside")
    fig3 = chart_style(fig3)
    fig3.update_xaxes(title="")
    with left_bottom:
        st.plotly_chart(fig3, width="stretch")

    # Chart 4: correctly weighted student response rates by department
    response = (
        filtered.groupby("Department", as_index=False)
        .agg(Respondents=("Respondent_No", "sum"), Enrolled=("Enrollment_No", "sum"))
    )
    response["Rate"] = 100 * response["Respondents"] / response["Enrolled"]
    fig4 = px.bar(
        response, x="Department", y="Rate", color="Department",
        color_discrete_map=DEPARTMENT_COLORS,
        title="Student response rate by department", text="Rate",
    )
    fig4.update_traces(texttemplate="%{y:.1f}%", textposition="outside")
    fig4 = chart_style(fig4, min_y=0, max_y=100, ylabel="Response rate (%)")
    fig4.update_layout(showlegend=False)
    with right_bottom:
        st.plotly_chart(fig4, width="stretch")

    st.caption("BBA is blue and CS is orange across all dashboard charts.")

with instructor_tab:
    st.subheader("Instructor performance")
    st.write("Explore instructor averages after applying your filters.")
    instructors = (
        filtered.groupby(["Instructor_Name", "Department"], as_index=False)
        .agg(Score=(metric_col, "mean"), Sections=("Sec", "size"))
        .sort_values("Score", ascending=False)
    )
    fig_ins = px.bar(
        instructors.head(12).sort_values("Score"),
        x="Score", y="Instructor_Name", color="Department", orientation="h",
        color_discrete_map=DEPARTMENT_COLORS,
        title=f"Top instructor-section averages: {metric_label}",
        hover_data=["Sections"],
    )
    fig_ins.update_layout(
        template="plotly_white", height=480,
        xaxis_range=[0, 5], xaxis_title="Average evaluation / 5",
        yaxis_title="", legend_title_text="",
        margin=dict(l=10, r=10, t=50, b=20),
    )
    st.plotly_chart(fig_ins, width="stretch")
    st.dataframe(
        instructors.rename(columns={
            "Instructor_Name": "Instructor", "Score": "Average score",
            "Sections": "Class sections"
        }).style.format({"Average score": "{:.2f}"}),
        width="stretch", hide_index=True,
    )

with data_tab:
    st.subheader("Filtered dataset")
    st.write("This section helps demonstrate how the charts are calculated.")
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.download_button(
        "Download filtered data as CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_instructor_evaluations.csv",
        mime="text/csv",
    )
    st.markdown(
        """**Methods**

- **Overall Score:** arithmetic mean of Teaching Skill, Material, and Human Skill for each section.
- **Department / year / category averages:** arithmetic mean of the selected section scores.
- **Student Response Rate:** sum of respondents divided by sum of enrollments (not the simple average of section percentages).
- **Interactive form:** year, department, semester, instructor, evaluation measure, and minimum enrollment.
- **Source:** `sample_instructor_evaluations.csv` (synthetic demo data), one row per class section.
"""
    )

st.divider()
st.caption("Portfolio project • Built with Python, Streamlit, pandas, and Plotly • Synthetic data")
