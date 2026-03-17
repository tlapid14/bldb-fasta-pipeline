import time
import argparse
from pathlib import Path
from Bio import Entrez


def batched(iterable, n):
    iterator = iter(iterable)
    while True:
        chunk = [item for _, item in zip(range(n), iterator)]
        if not chunk:
            return
        yield chunk


def read_ids(path):
    return [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def fetch_batch(ids, email, retries=3, pause=0.5):
    Entrez.email = email
    attempt = 0

    while True:
        try:
            handle = Entrez.efetch(
                db="protein",
                id=",".join(ids),
                rettype="fasta",
                retmode="text",
            )
            text = handle.read()
            handle.close()
            return text
        except Exception:
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(pause * attempt)


def write_versioned_accessions(fasta_path):
    fasta_path = Path(fasta_path)
    versioned_accessions = []

    for line in fasta_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(">"):
            versioned_accessions.append(line[1:].split()[0])

    out_path = fasta_path.parent / "accessions_versioned.txt"
    out_path.write_text("\n".join(versioned_accessions) + "\n", encoding="utf-8")
    print(f"Wrote versioned accessions -> {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch FASTA records from NCBI for a list of protein accessions."
    )
    parser.add_argument("--ids", default="mapping/accessions.txt", help="Input accession list")
    parser.add_argument("--out", default="data/all_sequences.fasta", help="Output FASTA file")
    parser.add_argument(
        "--email",
        required=True,
        help="Email address required by NCBI Entrez",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of accessions to fetch per batch",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.4,
        help="Pause between batches in seconds",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Append to an existing output FASTA if present",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise ValueError("batch-size must be a positive integer")

    ids = read_ids(args.ids)
    if not ids:
        raise ValueError(f"No accession IDs found in: {args.ids}")

    print(f"Total IDs to fetch: {len(ids)}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    start_index = 0
    if args.resume and out_path.exists():
        done = sum(
            1
            for line in out_path.read_text(encoding="utf-8").splitlines()
            if line.startswith(">")
        )
        start_index = done
        print(f"Resuming from ID #{start_index}")

    mode = "a" if args.resume else "w"
    with out_path.open(mode, encoding="utf-8") as handle:
        for batch_number, chunk in enumerate(
            batched(ids[start_index:], args.batch_size),
            start=start_index // args.batch_size + 1,
        ):
            text = fetch_batch(chunk, args.email)
            if text and not text.endswith("\n"):
                text += "\n"

            handle.write(text)
            print(f"Batch {batch_number}: wrote {len(chunk)} sequences")
            time.sleep(args.pause)

    print(f"Done. FASTA -> {out_path}")
    write_versioned_accessions(out_path)


if __name__ == "__main__":
    main()