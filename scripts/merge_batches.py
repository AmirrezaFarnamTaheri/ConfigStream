import argparse

from scripts.merge.core import merge_batches

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge batch outputs.")
    parser.add_argument(
        "--batch-glob",
        default="output_batch_*",
        help="Glob pattern for batch output directories",
    )
    parser.add_argument("--output-dir", default="output", help="Output directory")
    args = parser.parse_args()

    merge_batches(args.batch_glob, args.output_dir)
