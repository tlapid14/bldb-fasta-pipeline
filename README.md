# BLDB FASTA Pipeline

A Python pipeline for collecting beta-lactamase protein sequences from the **BLDB (Beta-Lactamase Database)** and preparing them for downstream bioinformatics analysis.

The workflow automatically:

1. Scrapes BLDB enzyme family pages  
2. Extracts NCBI protein accession IDs  
3. Fetches FASTA sequences from NCBI  
4. Renames FASTA headers using enzyme names  
5. Optionally splits the FASTA into smaller files  

This repository automates building curated protein sequence datasets for beta-lactamase research.

---

## Pipeline Overview

BLDB website  
↓  
`scrape_website.py`  
↓  
`mapping/accessions.txt`  
`mapping/accession_to_name.tsv`  
↓  
`fetch_fastas.py`  
↓  
`data/all_sequences.fasta`  
↓  
`rename_fasta_headers.py`  
↓  
`data/all_sequences_renamed.fasta`  
↓  
(optional)  
`split_fasta.py`  
↓  
`output/parts/`

---

## Installation

Clone the repository:

```bash
git clone https://github.com/tlapid14/bldb-fasta-pipeline.git
cd bldb-fasta-pipeline
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

Run the full pipeline:

```bash
python scripts/pipeline.py --email your_email@example.com
```

NCBI requires an email address for Entrez requests.

---

## Optional: Split FASTA

Split the output FASTA into smaller files:

```bash
python scripts/pipeline.py --email your_email@example.com --split
```

Change sequences per file:

```bash
python scripts/pipeline.py --email your_email@example.com --split --per-file 500
```

---

## Repository Structure

```
bldb-fasta-pipeline/
│
├── scripts/
│   ├── pipeline.py
│   ├── scrape_website.py
│   ├── fetch_fastas.py
│   ├── rename_fasta_headers.py
│   └── split_fasta.py
│
├── mapping/
│   └── .gitkeep
│
├── data/
│   └── .gitkeep
│
├── output/
│   └── .gitkeep
│
└── requirements.txt
```

---

## Notes

BLDB: http://www.bldb.eu  
NCBI Entrez API: https://www.ncbi.nlm.nih.gov/books/NBK25501/

FASTA files may become large depending on the number of accessions.

---

## Author

**Tomer Lapid**

GitHub:  
https://github.com/tlapid14