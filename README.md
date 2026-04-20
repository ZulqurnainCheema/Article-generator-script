# Article Generator Script (Simple Guide)

![Header](https://capsule-render.vercel.app/api?type=waving&height=160&text=Article%20Generator%20Script&fontAlignY=35&animation=twinkling&color=0:22c55e,100:14b8a6)

![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&pause=1200&color=0EA5E9&center=true&vCenter=true&width=900&lines=Write+less.+Publish+more.+%F0%9F%9A%80;One+CSV+row+%3D+one+article+job+%F0%9F%A7%A0;Less+clicking%2C+more+chilling+%E2%9C%A8)

Welcome to your content autopilot 🚀

This script fills and runs the SEOwriting form for you, one CSV row at a time.

Think of it like this:
- Each row in your CSV = one article job 🧾
- The script opens the browser, fills fields, clicks buttons, and moves to the next row 🤖

Fun fact:
- This is the "less clicking, more chilling" workflow 😎

## What You Need ✅

- Python 3.9 or newer 🐍
- Internet connection 🌐
- Access to your SEOwriting account 🔐

## First-Time Setup (One Time Only) 🛠️

Open a terminal in this folder and run:

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

## Step 1: Prepare Your CSV 📄

1. Copy `input.sample.csv` and rename the copy to `input.csv`.
2. Open `input.csv` in Excel or Google Sheets.
3. Keep the header row (first row) exactly as-is.
4. Add one article request per row.

Important:
- `keyword` should always be filled ⭐
- If you leave optional columns blank, the script uses default values from `config.json`.

## Step 2: Check `config.json` ⚙️

Open `config.json` and check these values:

- `csv.path`: should point to your CSV (usually `input.csv`).
- `row_start`: first row to run (usually `1`).
- `row_end`: last row to run (use a large number to run all).
- `browser.headless`: keep `false` so you can see what is happening.

Recommended defaults:
- Leave most settings as they are unless you know you need to change them 👍

## Step 3: Sign In Once (If Needed) 🔑

The script uses a saved browser profile folder:
- `browser.user_data_dir`

If your session is not saved yet:
1. Run the script once.
2. A browser opens.
3. Log in to SEOwriting manually.
4. Close the browser.
5. Run the script again.

## Step 4: Run the Script ▶️

Before you launch:
- Take a quick look at your CSV one more time 👀
- Make sure you are logged in ✅
- Optional but recommended: grab coffee ☕

```bash
python3 run.py
```

You will see progress like row numbers in the terminal 📈

## If You Want to Continue Later ⏭️

Use these in `config.json`:
- `row_start`: where to resume
- `row_end`: where to stop

Example:
- If row 1-20 already finished, set `row_start` to `21`.

## Common Issues 🧯

### Browser profile is locked

Cause: Chrome is already open with the same profile.

Fix:
- Close Chrome completely and run again.
- Or use a separate profile folder in `browser.user_data_dir`.

### "No CSV rows found"

Cause: file path is wrong or CSV is empty.

Fix:
- Confirm `csv.path` in `config.json`.
- Confirm your CSV has a header row and at least one data row.

### Script skips some fields

Cause: those CSV cells are blank.

Fix:
- Fill the CSV value, or keep blank if you want default behavior.

## Quick Start Checklist 🏁

1. Install requirements.
2. Create `input.csv` from the sample.
3. Fill your rows.
4. Check `config.json` (`csv.path`, row range, browser settings).
5. Run `python3 run.py`.

## Support This Project ⭐

If this script saves you time, please star this repository so more people can find it. It really helps 💚

## Need a Change? 💬

If you need an update or a custom change, contact me using one of these options:

1. Open an issue in this repository (recommended).
2. Send me a direct message with your requested change.
3. Email me your request: `your-email@example.com`.

When you contact me, include:
- What you want changed
- A sample CSV row (if relevant)
- Any deadline you have
