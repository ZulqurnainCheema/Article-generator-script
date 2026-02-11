# Article Generator Automation

This project automates the "1-Click Blog Post" flow with Playwright and runs it row-by-row from a CSV.

## Files
- `run.py` automation script
- `config.json` configuration (edit this)
- `input.sample.csv` example CSV format
- `requirements.txt` Python dependency

## Setup
```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

## Configure
Edit `config.json`:
- `browser.type`: `chromium` (default), `firefox`, or `webkit`
- `browser.user_data_dir`: browser profile directory (Chrome/Chromium user data dir or Firefox profile dir)
- `browser.profile_dir`: Chrome/Chromium profile name (ignored for Firefox/WebKit)
- `browser.executable_path`: path to the browser binary
- `browser.type`: `chromium` (default), `firefox`, or `webkit`
- `csv.path`: your CSV file path
- `steps[0].url`: the exact tool URL
- `steps[0].selects`: fixed dropdown selections
- `steps[0].selects_from_csv`: optional CSV overrides for dropdowns (empty = keep default)
- `steps[0].selects_after`: dropdowns that appear after toggles (e.g., Connect to Web date)
- `steps[0].selects_from_csv_after`: optional CSV overrides for those dropdowns
- `steps[0].inputs_from_csv_required`: required CSV fields (e.g., main keyword)
- `steps[0].inputs_from_csv`: optional CSV fields (skips empty to keep defaults)
- `steps[0].checkboxes`: fixed checkboxes
- `steps[0].checkboxes_from_csv`: optional CSV overrides for checkboxes
- `steps[0].clicks`: ordered button clicks with optional waits
- `steps[1]`: the "generation page" step (fill in URL + selectors once you confirm)

## Run
```bash
python3 run.py
```

Notes
- If Chrome is already open with the same profile, close it or use a separate profile to avoid profile-lock errors.
- `row_start` and `row_end` let you resume from a specific row.
- If scheduling is enabled, the script will prompt for a starting date.
