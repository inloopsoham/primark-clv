"""
run_all.py - run the whole pipeline with one command.

    python run_all.py              # everything, from scratch (about 1 minute)
    python run_all.py --skip-data  # reuse the existing synthetic data

Steps: 1 generate data -> 2 features -> 3 models -> 4 segments -> 5 loyalty value.
Afterwards everything the app needs is in the 'outputs' folder.
"""
import argparse
import time

from src import config as C


def step(n, total, title):
    print("\n" + "#" * 78)
    print(f"# STEP {n}/{total}: {title}")
    print("#" * 78)
    return time.time()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-data", action="store_true",
                    help="reuse the existing database instead of regenerating the data")
    args = ap.parse_args()
    t_all = time.time()

    from src import features, generate_data, loyalty, models, segments

    if args.skip_data and C.DB_PATH.exists():
        print("Skipping data generation (using the existing database).")
    else:
        t = step(1, 5, "Generate synthetic data")
        generate_data.generate()
        print(f"[step took {time.time() - t:.0f}s]")

    t = step(2, 5, "Build customer features")
    features.print_summary(features.build_all())
    print(f"[step took {time.time() - t:.0f}s]")

    t = step(3, 5, "Train models and predict CLV")
    models.run()
    print(f"[step took {time.time() - t:.0f}s]")

    t = step(4, 5, "Create segments and campaigns")
    segments.run()
    print(f"[step took {time.time() - t:.0f}s]")

    t = step(5, 5, "Value of the loyalty programme")
    loyalty.run()
    print(f"[step took {time.time() - t:.0f}s]")

    print(f"\nALL DONE in {time.time() - t_all:.0f} seconds. Outputs are in: {C.OUTPUT_DIR}")
    print("Next: start the app with   uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
