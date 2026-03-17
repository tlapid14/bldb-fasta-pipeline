import argparse
from pathlib import Path


def split_fasta(in_path, out_dir, per_file=1000, prefix="part"):
    in_path = Path(in_path)
    out_dir = Path(out_dir)

    if per_file <= 0:
        raise ValueError("per_file must be a positive integer")

    if not in_path.is_file():
        raise FileNotFoundError(f"Input FASTA not found: {in_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    file_idx = 1
    seq_in_file = 0
    out_handle = None
    saw_header = False

    def open_new_output():
        nonlocal out_handle, file_idx, seq_in_file
        if out_handle is not None:
            out_handle.close()

        out_path = out_dir / f"{prefix}_{file_idx}.fasta"
        out_handle = out_path.open("w", encoding="utf-8")
        file_idx += 1
        seq_in_file = 0

    with in_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                saw_header = True
                if out_handle is None or seq_in_file >= per_file:
                    open_new_output()
                seq_in_file += 1

            if out_handle is None:
                continue

            out_handle.write(line)

    if out_handle is not None:
        out_handle.close()

    if not saw_header:
        raise ValueError(f"No FASTA headers found in input file: {in_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Split a FASTA into files with a fixed number of sequences per file."
    )
    parser.add_argument("--in", dest="in_path", required=True, help="Input FASTA file")
    parser.add_argument("--outdir", default="data/parts", help="Output directory")
    parser.add_argument(
        "--per",
        dest="per_file",
        type=int,
        default=1000,
        help="Number of sequences per output file",
    )
    parser.add_argument("--prefix", default="part", help="Output file prefix")
    args = parser.parse_args()

    split_fasta(args.in_path, args.outdir, args.per_file, args.prefix)


if __name__ == "__main__":
    main()