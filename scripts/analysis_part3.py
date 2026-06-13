import sqlite3
import pandas as pd
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu

DB_PATH = "cell_counts.db"
FREQ_PATH = os.path.join("outputs", "cell_frequencies.csv")
OUT_STATS = os.path.join("outputs", "responder_vs_nonresponder_stats.csv")
OUT_DATA = os.path.join("outputs", "responder_comparison_data.csv")
PLOT_DIR = os.path.join("outputs", "plots")

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def main():
    freq_df = pd.read_csv(FREQ_PATH)

    conn = sqlite3.connect(DB_PATH)
    meta_df = pd.read_sql_query("""
        SELECT s.sample_id AS sample, s.sample_type, s.treatment, s.response, su.condition
        FROM samples s
        JOIN subjects su ON s.subject_id = su.subject_id
    """, conn)
    conn.close()

    merged = freq_df.merge(meta_df, on="sample")

    # melanoma, PBMC, miraclib only
    subset = merged[
        (merged["condition"] == "melanoma")
        & (merged["treatment"] == "miraclib")
        & (merged["sample_type"] == "PBMC")
    ].copy()

    os.makedirs(PLOT_DIR, exist_ok=True)
    subset.to_csv(OUT_DATA, index=False)

    results = []
    for pop in POPULATIONS:
        pop_data = subset[subset["population"] == pop]
        responders = pop_data[pop_data["response"] == "yes"]["percentage"]
        non_responders = pop_data[pop_data["response"] == "no"]["percentage"]

        if len(responders) > 0 and len(non_responders) > 0:
            stat, pval = mannwhitneyu(responders, non_responders, alternative="two-sided")
        else:
            stat, pval = float("nan"), float("nan")

        results.append({
            "population": pop,
            "n_responders": len(responders),
            "n_non_responders": len(non_responders),
            "mean_responders": round(responders.mean(), 4) if len(responders) else None,
            "mean_non_responders": round(non_responders.mean(), 4) if len(non_responders) else None,
            "mann_whitney_u": stat,
            "p_value": pval,
            "significant_p<0.05": pval < 0.05 if pval == pval else False,
        })

        plt.figure(figsize=(5, 5))
        sns.boxplot(data=pop_data, x="response", y="percentage", order=["no", "yes"])
        sns.stripplot(data=pop_data, x="response", y="percentage", order=["no", "yes"],
                       color="black", alpha=0.5, size=4)
        plt.title(f"{pop} relative frequency\nresponders vs non-responders (p={pval:.4f})")
        plt.xlabel("response")
        plt.ylabel("relative frequency (%)")
        plt.tight_layout()
        plt.savefig(os.path.join(PLOT_DIR, f"boxplot_{pop}.png"), dpi=120)
        plt.close()

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUT_STATS, index=False)
    print(results_df)
    print(f"wrote {OUT_STATS} and boxplots to {PLOT_DIR}/")


if __name__ == "__main__":
    main()
