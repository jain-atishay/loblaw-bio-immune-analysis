import sqlite3
import pandas as pd
import os

DB_PATH = "cell_counts.db"
OUT_SUBSET = os.path.join("outputs", "baseline_subset.csv")
OUT_SUMMARY = os.path.join("outputs", "baseline_summary.csv")


def main():
    conn = sqlite3.connect(DB_PATH)

    subset = pd.read_sql_query("""
        SELECT s.sample_id AS sample, su.subject_id, su.project_id AS project,
               su.condition, su.sex, su.age, s.treatment, s.response,
               s.sample_type, s.time_from_treatment_start
        FROM samples s
        JOIN subjects su ON s.subject_id = su.subject_id
        WHERE su.condition = 'melanoma'
          AND s.sample_type = 'PBMC'
          AND s.treatment = 'miraclib'
          AND s.time_from_treatment_start = 0
    """, conn)
    conn.close()

    os.makedirs("outputs", exist_ok=True)
    subset.to_csv(OUT_SUBSET, index=False)

    lines = []

    by_project = subset.groupby("project")["sample"].nunique()
    lines.append("samples per project:")
    lines.append(by_project.to_string())
    lines.append("")

    by_response = subset.groupby("response")["subject_id"].nunique()
    lines.append("subjects by response:")
    lines.append(by_response.to_string())
    lines.append("")

    by_sex = subset.groupby("sex")["subject_id"].nunique()
    lines.append("subjects by sex:")
    lines.append(by_sex.to_string())
    lines.append("")

    # avg b cell count, melanoma male responders, t=0
    conn = sqlite3.connect(DB_PATH)
    bcell_df = pd.read_sql_query("""
        SELECT su.sex, s.response, cc.count
        FROM samples s
        JOIN subjects su ON s.subject_id = su.subject_id
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        JOIN cell_populations cp ON cc.population_id = cp.population_id
        WHERE su.condition='melanoma' AND s.sample_type='PBMC' AND s.treatment='miraclib'
          AND s.time_from_treatment_start=0 AND cp.population_name='b_cell'
    """, conn)
    conn.close()

    male_resp = bcell_df[(bcell_df["sex"] == "M") & (bcell_df["response"] == "yes")]
    avg_bcell = round(male_resp["count"].mean(), 2)
    lines.append(f"avg b cell count, melanoma male responders, t=0: {avg_bcell:.2f}")

    with open(OUT_SUMMARY, "w") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print(f"wrote {OUT_SUBSET} and {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
