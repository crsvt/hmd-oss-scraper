# HMD Open Source Tracker

## What is this?

HMD doesn't offer an official feed or API for their open source releases. This makes it hard to track when new kernel sources for their devices are published.

This repo solves that problem. It's a simple, automated tracker that scrapes the [HMD Open Source page](https://www.hmd.com/en_int/opensource) and commits any new files it finds.

## How it Works

The process is fully automated using GitHub Actions:

1.  **Schedule:** The workflow runs twice a week (Tue & Fri @ 8:30 AM IST). It can also be triggered manually from the Actions tab.
2.  **Scrape:** It runs the `scraper.py` script to fetch the latest device list from HMD's website.
3.  **Compare & Commit:** The script compares the new data to the existing `data/hmd_versions.json`. If anything has changed, the script updates both the JSON and the `.sh` files, and the workflow commits the changes back to this repo. If there are no changes, no new commit is made.

## The Files

The scraper generates two key files:

*   `data/hmd_versions.json`: The primary data file. It's structured and easy to parse, making it perfect for use in other scripts or projects.
*   `data/hmd_versions.sh`: A shell script that sources the same data into a Bash array. Provided for convenience.

## Disclaimer

*   **Unofficial:** This project is not affiliated with or endorsed by HMD Global or Nokia.
*   **Data is "As Is":** The data is scraped directly from the public website. I can't guarantee it's always 100% accurate or complete.
*   **The Scraper Can Break:** This relies on the HMD website's HTML structure. If they update their site, the script might break until I can fix it.
*   **Use at Your Own Risk:** You are responsible for how you use the data and scripts in this repository.

## License

MIT - See the `LICENSE` file for details.
