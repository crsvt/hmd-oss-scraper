import requests
from bs4 import BeautifulSoup
import os
import re
import json

def scrape_hmd_opensource():
    """Scrapes the HMD website for device open source files."""
    url = "https://www.hmd.com/en_int/opensource"
    print("Fetching latest data from HMD website...")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
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
                    versions_with_links.append({"name": version_name, "link": href})
            
            if versions_with_links:
                devices[device_name] = versions_with_links[::-1]

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

    if not new_data:
        print("Could not retrieve new data. Exiting.")
    else:
        if old_data == new_data:
            print(f"\nNo new versions found. Files are already up-to-date.")
        else:
            print("\nChanges detected. Writing updated files...")
            write_to_json(new_data, JSON_FILENAME)
            write_to_shell_script(new_data, SHELL_FILENAME)
            print(f"Successfully updated '{JSON_FILENAME}' and '{SHELL_FILENAME}'.")