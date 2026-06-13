import subprocess
import sys

py = sys.executable

steps = [
    [py, "load_data.py"],
    [py, "scripts/analysis_part2.py"],
    [py, "scripts/analysis_part3.py"],
    [py, "scripts/analysis_part4.py"],
]

for step in steps:
    print(f"\n=== {' '.join(step)} ===")
    result = subprocess.run(step)
    if result.returncode != 0:
        sys.exit(result.returncode)

print("\ndone - check outputs/")
