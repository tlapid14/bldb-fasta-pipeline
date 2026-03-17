import sys
import argparse
import subprocess
from pathlib import Path


def run(cmd):
    print(">>>", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Command failed with exit code {exc.returncode}: {' '.join(cmd)}") from exc


def ensure_dirs():
    for folder in ["mapping", "data", "output"]:
        Path(folder).mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Run the BLDB scraping and FASTA processing pipeline."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address required by NCBI Entrez.",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Also split the renamed FASTA into smaller files.",
    )
    parser.add_argument(
        "--per-file",
        type=int,
        default=1000,
        help="Number of sequences per split FASTA file.",
    )
    args = parser.parse_args()

    if args.per_file <= 0:
        raise ValueError("--per-file must be a positive integer")

    ensure_dirs()

    run([sys.executable, "scripts/scrape_website.py"])

    run([
        sys.executable,
        "scripts/fetch_fastas.py",
        "--email", args.email,
        "--ids", "mapping/accessions.txt",
        "--out", "data/all_sequences.fasta",
    ])

    run([
        sys.executable,
        "scripts/rename_fasta_headers.py",
        "data/all_sequences.fasta",
        "mapping/accession_to_name.tsv",
        "data/all_sequences_renamed.fasta",
    ])

    if args.split:
        run([
            sys.executable,
            "scripts/split_fasta.py",
            "--in", "data/all_sequences_renamed.fasta",
            "--outdir", "output/parts",
            "--per", str(args.per_file),
            "--prefix", "part",
        ])


if __name__ == "__main__":
    main()