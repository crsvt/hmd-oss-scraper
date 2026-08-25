import requests
from bs4 import BeautifulSoup
import os
import re
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

URL = "https://www.hmd.com/en_int/opensource"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_ATTEMPTS = 5
TIMEOUT = 30

def fetch_page():
    """Fetches the open source page, retrying on transient upstream errors."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(URL, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            status = getattr(e.response, 'status_code', None)
            retryable = status is None or status >= 500 or status == 429
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed: {e}")
            if not retryable or attempt == MAX_ATTEMPTS:
                return None
            delay = 5 * (2 ** (attempt - 1))
            print(f"Retrying in {delay}s...")
            time.sleep(delay)
    return None

def scrape_hmd_opensource():
    """Scrapes the HMD website for device open source files."""
    print("Fetching latest data from HMD website...")
    response = fetch_page()
    if response is None:
        print("Error: could not fetch the URL after retries.")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    devices = {}
    details_tags = soup.find_all('details', class_='e1fobdx71')

    for tag in details_tags:
        device_name_tag = tag.find('div', class_='er4s1o93')
        if device_name_tag:
            device_name = " ".join(device_name_tag.text.strip().split())
            
            versions_with_links = []
            links = tag.find_all('a')
            for link in links:
                version_name = link.text.strip()
                href = link.get('href', '').strip()

                if href.startswith('//'):
                    href = 'https:' + href
                elif 'azureedge.net' in href and not href.startswith('http'):
                    href = 'https://' + href
                
                if version_name and href:
                    entry = {"name": version_name, "link": href}
                    # HMD's page sometimes lists the same archive twice.
                    if entry not in versions_with_links:
                        versions_with_links.append(entry)
            
            if versions_with_links:
                devices[device_name] = versions_with_links[::-1]

    return devices


def probe_archive(entry):
    """HEADs an archive URL to record its current identity on the CDN.

    HMD sometimes re-uploads a corrected package under the SAME filename and
    URL, so name/link alone cannot detect that the contents changed. The
    blob's ETag does.
    """
    try:
        r = requests.head(entry["link"], headers=HEADERS,
                          timeout=TIMEOUT, allow_redirects=True)
        if r.status_code >= 400:
            return entry["link"], None, None
        etag = r.headers.get("ETag", "").strip('"') or None
        size = r.headers.get("Content-Length")
        return entry["link"], etag, int(size) if size and size.isdigit() else None
    except requests.exceptions.RequestException:
        return entry["link"], None, None


def enrich_with_etags(devices):
    """Annotates every release with the CDN ETag and size of its archive."""
    unique = {}
    for versions in devices.values():
        for v in versions:
            unique.setdefault(v["link"], v)

    print(f"Probing {len(unique)} archive URLs for changes...")
    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for link, etag, size in pool.map(probe_archive, unique.values()):
            results[link] = (etag, size)

    unreachable = 0
    for versions in devices.values():
        for v in versions:
            etag, size = results.get(v["link"], (None, None))
            v["etag"] = etag
            v["size"] = size
            if etag is None:
                unreachable += 1

    if unreachable:
        print(f"Warning: {unreachable} archive(s) unreachable; recorded with null etag.")
    return devices

def read_from_json(filename="data/hmd_releases.json"):
    """Reads device data from the JSON file."""
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {filename}. Starting fresh.")
        return {}

def write_to_json(devices, filename="data/hmd_releases.json"):
    """Writes device data to the JSON file with nice formatting."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(devices, f, indent=2)

def write_to_shell_script(devices, filename="data/hmd_releases.sh"):
    """Writes the device data to a shell script file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n")
        f.write("# This script contains open source version information and download links for HMD devices.\n")
        f.write("# Generated automatically. Device order matches the HMD website.\n\n")

        for device_name, versions in devices.items():
            f.write(f'DEVICE_HUMAN="{device_name}"\n')
            f.write("# Oldest -> Newest\n")
            f.write("VERSIONS=(\n")
            for version_info in versions:
                f.write(f'  # {version_info["link"]}\n')
                f.write(f'  "{version_info["name"]}"\n')
            f.write(")\n\n")

if __name__ == "__main__":
    JSON_FILENAME = "data/hmd_releases.json"
    SHELL_FILENAME = "data/hmd_releases.sh"
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(JSON_FILENAME), exist_ok=True)

    print(f"Checking for existing file '{JSON_FILENAME}'...")
    old_data = read_from_json(JSON_FILENAME)
    
    new_data = scrape_hmd_opensource()
    if new_data:
        new_data = enrich_with_etags(new_data)

    if not new_data:
        print("Could not retrieve new data. Exiting.")
        sys.exit(1)
    else:
        if old_data == new_data:
            print(f"\nNo new versions found. Files are already up-to-date.")
        else:
            print("\nChanges detected. Writing updated files...")
            write_to_json(new_data, JSON_FILENAME)
            write_to_shell_script(new_data, SHELL_FILENAME)
            print(f"Successfully updated '{JSON_FILENAME}' and '{SHELL_FILENAME}'.")