
import csv
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BASE = "https://tranco-list.eu"
TIMEOUT = 60
USER_AGENT = "TrancoMetadataLookup/1.0"


def get_domain(user_input):
    value = user_input.strip()

    # Allow entering either a URL or a bare domain.
    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")

    if not host or "." not in host:
        raise ValueError("Invalid website URL or domain.")

    return host.encode("idna").decode("ascii")


def fetch_json(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


def get_latest_list():
    # Metadata for the current standard Tranco list.
    return fetch_json(f"{BASE}/api/lists/date/latest")


def find_rank_in_list(domain, list_id, download_url=None):
    # Prefer the download URL provided by Tranco's own metadata.
    if not download_url:
        download_url = f"{BASE}/download/{list_id}/1000000"

    request = Request(download_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT) as response:
        content = response.read()

    # Tranco list downloads are commonly ZIP files containing CSV data.
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if not names:
                raise RuntimeError("The Tranco archive is empty.")
            with archive.open(names[0]) as file:
                text = io.TextIOWrapper(file, encoding="utf-8-sig")
                return scan_csv(text, domain)

    text = content.decode("utf-8-sig")
    return scan_csv(io.StringIO(text), domain)


def scan_csv(file_obj, target_domain):
    for row in csv.reader(file_obj):
        if len(row) < 2:
            continue

        first = row[0].strip().lower()
        second = row[1].strip()

        # Standard Tranco CSV rows: rank,domain
        if first.isdigit():
            rank, domain = int(first), second
        # Also accept domain,rank if the file uses that order.
        elif second.isdigit():
            domain, rank = row[0].strip().lower(), int(second)
        else:
            continue

        if domain.rstrip(".").lower() == target_domain:
            return rank

    return None


def main():
    user_input = input("Enter website URL: ").strip()
    domain = get_domain(user_input)

    print("Fetching latest Tranco list metadata...")
    metadata = get_latest_list()

    list_id = metadata.get("list_id")
    created_on = metadata.get("created_on")
    download_url = metadata.get("download")

    if not list_id or not created_on:
        raise RuntimeError(
            "Tranco response did not contain list_id and created_on. "
            "Inspect the returned metadata before proceeding."
        )

    # Preserve the source timestamp and derive its UTC calendar date.
    created_dt = datetime.fromisoformat(
        created_on.replace("Z", "+00:00")
    ).astimezone(timezone.utc)

    rank = find_rank_in_list(domain, list_id, download_url)

    result = {
        "domain": domain,
        "list_id": list_id,
        "list_date": created_dt.strftime("%Y-%m-%d"),
        "rank": str(rank) if rank is not None else "NOT_IN_LIST",
        "source": f"{BASE}/list/{list_id}",
    }

    print("\nResult:")
    print(json.dumps(result, indent=4, ensure_ascii=False))

    filename = re.sub(r"[^a-zA-Z0-9.-]", "_", domain) + "_tranco.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)

    print(f"\nSaved to: {filename}")


if __name__ == "__main__":
    try:
        main()
    except URLError as exc:
        print(f"Network/API error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
