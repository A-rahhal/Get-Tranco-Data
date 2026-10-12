# Tranco domain rank lookup

This script looks up a website's rank in the latest standard Tranco list and
saves the result as a JSON file.

## Requirements

- Python 3.7 or newer
- Internet access
- No third-party Python packages are required

## Run on Windows

1. Copy `get_tranco_data.py` to the target computer.
2. Open PowerShell in the folder containing the script.
3. Run:

   ```powershell
   py get_tranco_data.py
   ```

4. Enter a domain (such as `example.com`) or a full URL when prompted.

The result is printed and saved as `<domain>_tranco.json` in the current
folder. The script retrieves current data from `tranco-list.eu`, so an internet
connection is required.
