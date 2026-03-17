import sys
import re


def load_map(tsv_path: str) -> dict[str, str]:
    mapping: dict[str, str] = {}

    with open(tsv_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            accession = parts[0].strip()
            name = parts[1].strip()

            if accession and name:
                mapping[accession] = name

    return mapping


def strip_version(accession: str) -> str:
    return re.sub(r"\.\d+$", "", accession)


def main():
    if len(sys.argv) != 4:
        print("Usage: python rename_fasta_headers.py <in_fasta> <mapping_tsv> <out_fasta>")
        sys.exit(1)

    in_fasta, mapping_tsv, out_fasta = sys.argv[1], sys.argv[2], sys.argv[3]
    mapping = load_map(mapping_tsv)

    renamed = 0
    kept = 0
    used_base_fallback = 0

    with open(in_fasta, "r", encoding="utf-8") as fin, open(out_fasta, "w", encoding="utf-8") as fout:
        for line in fin:
            if line.startswith(">"):
                header = line[1:].strip()
                accession = header.split()[0]
                accession = accession.split("|")[0]

                name = mapping.get(accession)
                if name is None:
                    base_accession = strip_version(accession)
                    name = mapping.get(base_accession)
                    if name is not None:
                        used_base_fallback += 1

                if name is not None:
                    fout.write(f">{accession} {name}\n")
                    renamed += 1
                else:
                    fout.write(f">{accession}\n")
                    kept += 1
            else:
                fout.write(line)

    print(f"Renamed headers: {renamed}")
    print(f"Used base-accession fallback (AAA.1 -> AAA): {used_base_fallback}")
    print(f"Headers without mapping (kept as just accession): {kept}")
    print(f"Output: {out_fasta}")


if __name__ == "__main__":
    main()