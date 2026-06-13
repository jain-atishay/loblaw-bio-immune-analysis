import sqlite3
import pandas as pd
import os

DB_PATH = "cell_counts.db"
CSV_PATH = os.path.join("data", "cell-count.csv")

# normalized schema - projects -> subjects -> samples -> cell_counts (long format)
SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id   TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS subjects (
    subject_id   TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    condition    TEXT,
    age          INTEGER,
    sex          TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS samples (
    sample_id                 TEXT PRIMARY KEY,
    subject_id                TEXT NOT NULL,
    sample_type               TEXT,
    treatment                 TEXT,
    response                  TEXT,
    time_from_treatment_start INTEGER,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

CREATE TABLE IF NOT EXISTS cell_populations (
    population_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    population_name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS cell_counts (
    sample_id       TEXT NOT NULL,
    population_id   INTEGER NOT NULL,
    count           INTEGER NOT NULL,
    PRIMARY KEY (sample_id, population_id),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (population_id) REFERENCES cell_populations(population_id)
);
"""

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def main():
    df = pd.read_csv(CSV_PATH)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    for project_id in df["project"].unique():
        cur.execute("INSERT OR IGNORE INTO projects (project_id) VALUES (?)", (project_id,))

    # one row per subject - drop_duplicates keeps first occurrence which is fine
    # since age/sex/condition shouldn't change between samples
    subj_df = df.drop_duplicates(subset=["subject"])
    for _, row in subj_df.iterrows():
        cur.execute(
            "INSERT OR IGNORE INTO subjects (subject_id, project_id, condition, age, sex) VALUES (?, ?, ?, ?, ?)",
            (row["subject"], row["project"], row["condition"], int(row["age"]), row["sex"]),
        )

    for _, row in df.iterrows():
        cur.execute(
            """INSERT OR IGNORE INTO samples
               (sample_id, subject_id, sample_type, treatment, response, time_from_treatment_start)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (row["sample"], row["subject"], row["sample_type"], row["treatment"],
             row["response"], row["time_from_treatment_start"]),
        )

    for pop in POPULATIONS:
        cur.execute("INSERT OR IGNORE INTO cell_populations (population_name) VALUES (?)", (pop,))

    pop_id_map = dict(cur.execute("SELECT population_name, population_id FROM cell_populations").fetchall())

    # long format - one row per sample/population pair
    for _, row in df.iterrows():
        for pop in POPULATIONS:
            cur.execute(
                "INSERT OR REPLACE INTO cell_counts (sample_id, population_id, count) VALUES (?, ?, ?)",
                (row["sample"], pop_id_map[pop], int(row[pop])),
            )

    conn.commit()
    conn.close()
    print(f"done - wrote {DB_PATH}")


if __name__ == "__main__":
    main()
