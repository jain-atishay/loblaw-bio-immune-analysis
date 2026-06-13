# dashboard for the immune cell population analysis
# run with: streamlit run dashboard/app.py

import streamlit as st
import pandas as pd
import sqlite3
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "cell_counts.db")

st.set_page_config(page_title="Loblaw Bio - Immune Cell Dashboard", layout="wide")
st.title("Immune Cell Population Dashboard")
st.caption("Loblaw Bio | miraclib clinical trial analysis")

if not os.path.exists(DB_PATH):
    st.error("Database not found. Run `python load_data.py` first (or `make pipeline`).")
    st.stop()


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    cc_query = """
    SELECT cc.sample_id AS sample, cp.population_name AS population, cc.count AS count
    FROM cell_counts cc
    JOIN cell_populations cp ON cc.population_id = cp.population_id
    """
    long_df = pd.read_sql_query(cc_query, conn)

    meta_query = """
    SELECT s.sample_id AS sample, s.sample_type, s.treatment, s.response,
           s.time_from_treatment_start, su.subject_id, su.project_id AS project,
           su.condition, su.sex, su.age
    FROM samples s
    JOIN subjects su ON s.subject_id = su.subject_id
    """
    meta_df = pd.read_sql_query(meta_query, conn)
    conn.close()

    totals = long_df.groupby("sample")["count"].sum().rename("total_count")
    long_df = long_df.merge(totals, on="sample")
    long_df["percentage"] = (long_df["count"] / long_df["total_count"] * 100)
    long_df = long_df.merge(meta_df, on="sample")
    return long_df


df = load_data()
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

tab1, tab2, tab3 = st.tabs([
    "Part 2: Frequency Overview",
    "Part 3: Responder vs Non-responder",
    "Part 4: Baseline Subset",
])

# ---------------- Part 2 ----------------
with tab1:
    st.header("Cell Population Frequencies per Sample")
    samples = sorted(df["sample"].unique())
    selected = st.multiselect("Filter by sample (optional)", samples)
    view = df if not selected else df[df["sample"].isin(selected)]
    table = view[["sample", "total_count", "population", "count", "percentage"]].copy()
    table["percentage"] = table["percentage"].round(2)
    table = table.sort_values(["sample", "population"])
    st.dataframe(table, use_container_width=True, height=400)
    st.download_button(
        "Download full frequency table (CSV)",
        df[["sample", "total_count", "population", "count", "percentage"]]
            .sort_values(["sample", "population"]).to_csv(index=False),
        file_name="cell_frequencies.csv",
    )

# ---------------- Part 3 ----------------
with tab2:
    st.header("Melanoma PBMC, miraclib: Responders vs Non-responders")

    subset = df[
        (df["condition"] == "melanoma")
        & (df["treatment"] == "miraclib")
        & (df["sample_type"] == "PBMC")
    ]

    if subset.empty:
        st.warning("No matching samples found.")
    else:
        results = []
        for pop in POPULATIONS:
            pop_data = subset[subset["population"] == pop]
            r = pop_data[pop_data["response"] == "yes"]["percentage"]
            nr = pop_data[pop_data["response"] == "no"]["percentage"]
            if len(r) > 0 and len(nr) > 0:
                stat, pval = mannwhitneyu(r, nr, alternative="two-sided")
            else:
                stat, pval = float("nan"), float("nan")
            results.append({
                "population": pop,
                "n_responders": len(r),
                "n_non_responders": len(nr),
                "mean_responders (%)": round(r.mean(), 2) if len(r) else None,
                "mean_non_responders (%)": round(nr.mean(), 2) if len(nr) else None,
                "p_value": round(pval, 4) if pval == pval else None,
                "significant (p<0.05)": (pval < 0.05) if pval == pval else False,
            })

        results_df = pd.DataFrame(results)
        st.subheader("Statistical Summary (Mann-Whitney U test)")
        st.dataframe(results_df, use_container_width=True)

        sig = results_df[results_df["significant (p<0.05)"]]["population"].tolist()
        if sig:
            st.success(f"Significant difference (p<0.05) found for: {', '.join(sig)}")
        else:
            st.info("No populations reached significance at p<0.05.")

        st.subheader("Boxplots: Relative Frequency by Response Status")
        cols = st.columns(2)
        for i, pop in enumerate(POPULATIONS):
            pop_data = subset[subset["population"] == pop]
            fig, ax = plt.subplots(figsize=(4, 4))
            sns.boxplot(data=pop_data, x="response", y="percentage", order=["no", "yes"], ax=ax)
            sns.stripplot(data=pop_data, x="response", y="percentage", order=["no", "yes"],
                           color="black", alpha=0.5, size=3, ax=ax)
            ax.set_title(pop)
            ax.set_xlabel("Response")
            ax.set_ylabel("Relative frequency (%)")
            with cols[i % 2]:
                st.pyplot(fig)
            plt.close(fig)

# ---------------- Part 4 ----------------
with tab3:
    st.header("Melanoma, miraclib, PBMC, Baseline (t=0)")

    baseline = df[
        (df["condition"] == "melanoma")
        & (df["treatment"] == "miraclib")
        & (df["sample_type"] == "PBMC")
        & (df["time_from_treatment_start"] == 0)
    ]

    base_samples = baseline.drop_duplicates(subset=["sample"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total samples", base_samples["sample"].nunique())
        st.write("**Samples per project**")
        st.dataframe(base_samples.groupby("project")["sample"].nunique().rename("n_samples"))
    with col2:
        st.write("**Subjects by response**")
        st.dataframe(base_samples.groupby("response")["subject_id"].nunique().rename("n_subjects"))
    with col3:
        st.write("**Subjects by sex**")
        st.dataframe(base_samples.groupby("sex")["subject_id"].nunique().rename("n_subjects"))

    st.subheader("Average B-cell count: Melanoma male responders at t=0")
    bcell = baseline[
        (baseline["population"] == "b_cell")
        & (baseline["sex"] == "M")
        & (baseline["response"] == "yes")
    ]
    avg_b = bcell["count"].mean()
    st.metric("Average B cell count", f"{avg_b:.2f}")

    st.subheader("Underlying subset")
    st.dataframe(base_samples[["sample", "subject_id", "project", "sex", "response"]],
                  use_container_width=True, height=300)
