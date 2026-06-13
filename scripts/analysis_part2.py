import sqlite3
import pandas as pd
import os

DB_PATH = "cell_counts.db"
OUT_PATH = os.path.join("outputs", "cell_frequencies.csv")


def main():
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT cc.sample_id AS sample, cp.population_name AS population, cc.count AS count
    FROM cell_counts cc
    JOIN cell_populations cp ON cc.population_id = cp.population_id
    """
    long_df = pd.read_sql_query(query, conn)
    conn.close()

    totals = long_df.groupby("sample")["count"].sum().rename("total_count")
    long_df = long_df.merge(totals, on="sample")
    long_df["percentage"] = (long_df["count"] / long_df["total_count"] * 100).round(4)

    long_df = long_df[["sample", "total_count", "population", "count", "percentage"]]
    long_df = long_df.sort_values(["sample", "population"]).reset_index(drop=True)

    os.makedirs("outputs", exist_ok=True)
    long_df.to_csv(OUT_PATH, index=False)
    print(f"wrote {OUT_PATH} ({len(long_df)} rows)")


if __name__ == "__main__":
    main()
