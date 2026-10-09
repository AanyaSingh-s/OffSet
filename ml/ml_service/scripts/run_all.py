"""Run the full pipeline in order (generation, features, validation, training, evaluation, figures, tables)."""
import subprocess
import sys
from pathlib import Path

STEPS = ["01_generate_data.py", "02_build_features.py", "03_validate_data.py", "04_train.py",
         "05_evaluate.py", "06_make_figures.py", "07_results_tables.py"]


def main() -> None:
    here = Path(__file__).parent
    for step in STEPS:
        print(f"==> {step}", flush=True)
        subprocess.run([sys.executable, str(here / step), *sys.argv[1:]] if step.startswith("01") and sys.argv[1:] else
                       [sys.executable, str(here / step)], check=True)


if __name__ == "__main__":
    main()
