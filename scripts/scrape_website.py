import re
import time
import pathlib
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup


INDEX_URL = "http://www.bldb.eu/Enzymes.php"
BASE_URL = "http://www.bldb.eu"

OUT_TSV = pathlib.Path("mapping/accession_to_name.tsv")
OUT_TXT = pathlib.Path("mapping/accessions.txt")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

ACCESSION_IN_NCBI_LINK = re.compile(
    r"ncbi\.nlm\.nih\.gov/protein/([A-Za-z0-9_\.]+)",
    re.IGNORECASE,
)
ENZYME_TOKEN = re.compile(r"\b[A-Z0-9]{2,8}-\d+\b")

BAD_ACCESSION_WORDS = {"sequence", "seq", "protein", "name", "id", "accession", "gi"}
MISSING_TOKENS = {"—", "–", "-", ""}


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
    )

    retry = Retry(
        total=6,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


SESSION = make_session()


def get_soup(url: str) -> BeautifulSoup:
    response = SESSION.get(url, timeout=40, allow_redirects=True)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def get_family_urls(index_url: str, base_url: str) -> list[str]:
    soup = get_soup(index_url)
    family_urls: list[str] = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href:
            continue

        absolute_url = urljoin(base_url + "/", href)
        parsed = urlparse(absolute_url)

        if parsed.path.endswith("BLDB.php"):
            query = parse_qs(parsed.query)
            prot_values = query.get("prot", [])
            if prot_values:
                prot = prot_values[0].strip()
                key = (parsed.scheme, parsed.netloc, parsed.path, prot)
                if key not in seen:
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?prot={prot}"
                    family_urls.append(clean_url)
                    seen.add(key)

    if not family_urls:
        fallback_prots = ["A", "B1", "B2", "B3", "C", "D"]
        family_urls = [f"{base_url}/BLDB.php?prot={prot}" for prot in fallback_prots]

    return family_urls


def normalize_accession(accession: str) -> str | None:
    if not accession:
        return None

    value = accession.strip()
    if not value:
        return None

    lower_value = value.lower()
    if lower_value in BAD_ACCESSION_WORDS:
        return None
    if value in MISSING_TOKENS:
        return None

    has_letter = any(char.isalpha() for char in value)
    has_digit = any(char.isdigit() for char in value)
    if not (has_letter and has_digit):
        return None

    if not re.fullmatch(r"[A-Za-z0-9_\.]+", value):
        return None

    if len(value) < 5:
        return None

    return value


def extract_accessions_from_row(row) -> set[str]:
    accessions: set[str] = set()

    for anchor in row.find_all("a", href=True):
        href = anchor["href"]
        match = ACCESSION_IN_NCBI_LINK.search(href)
        if match:
            accession = normalize_accession(match.group(1))
            if accession:
                accessions.add(accession)

    if accessions:
        return accessions

    row_text = row.get_text(" ", strip=True)
    if not row_text:
        return accessions

    for token in re.split(r"[\s,;]+", row_text):
        candidate = normalize_accession(token)
        if candidate:
            accessions.add(candidate)

    return accessions


def looks_like_pure_enzyme_cell(text: str) -> str | None:
    if not text:
        return None

    cleaned = re.sub(r"[\*\u2020\u00B9\u00B2\u00B3]+", "", text.strip()).strip()
    match = re.fullmatch(r"([A-Z0-9]{2,8}-\d+)", cleaned)
    if match:
        return match.group(1)

    return None


def extract_enzyme_name_from_row(row) -> str | None:
    cells = row.find_all(["td", "th"])
    if not cells:
        return None

    for cell in cells:
        text = cell.get_text(" ", strip=True)
        hit = looks_like_pure_enzyme_cell(text)
        if hit:
            return hit

    candidates: list[tuple[int, str]] = []

    for cell in cells:
        text = cell.get_text(" ", strip=True)
        if not text:
            continue

        hits = ENZYME_TOKEN.findall(text)
        for hit in hits:
            like_pattern = re.compile(
                rf"\b{re.escape(hit)}\b\s*[-–—]?\s*like\b",
                re.IGNORECASE,
            )
            if like_pattern.search(text):
                continue

            candidates.append((len(text), hit))

    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    return None


def scrape_family_page(url: str) -> dict[str, str]:
    soup = get_soup(url)
    mapping: dict[str, str] = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            enzyme = extract_enzyme_name_from_row(row)
            if not enzyme:
                continue

            accessions = extract_accessions_from_row(row)
            if not accessions:
                continue

            for accession in accessions:
                mapping[accession] = enzyme

    return mapping


def main():
    print(f"[1/3] Loading index: {INDEX_URL}")
    family_urls = get_family_urls(INDEX_URL, BASE_URL)
    print(f"      Found {len(family_urls)} family pages")

    print("[2/3] Scanning families for accession -> enzyme name...")
    final_map: dict[str, str] = {}

    for index, family_url in enumerate(family_urls, 1):
        try:
            family_mapping = scrape_family_page(family_url)
            final_map.update(family_mapping)
            print(
                f"      [{index:>2}/{len(family_urls)}] "
                f"{family_url}  ->  {len(family_mapping)} mappings"
            )
        except requests.RequestException as exc:
            print(f"      [{index:>2}/{len(family_urls)}] {family_url}  x  {exc}")

        time.sleep(0.4)

    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_TSV.open("w", encoding="utf-8", newline="\n") as handle:
        for accession in sorted(final_map):
            handle.write(f"{accession}\t{final_map[accession]}\n")

    with OUT_TXT.open("w", encoding="utf-8", newline="\n") as handle:
        for accession in sorted(final_map):
            handle.write(accession + "\n")

    print(f"[3/3] Wrote {len(final_map)} mappings -> {OUT_TSV}")
    print(f"      Wrote {len(final_map)} accessions -> {OUT_TXT}")
    print("Done")


if __name__ == "__main__":
    main()