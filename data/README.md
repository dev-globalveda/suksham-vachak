# Cricsheet Data

## Sample Data (Included)

The cricsheet_sample/ folder contains 20 sample matches for quick testing and development.

## Full Dataset (Not in repo - too large)

The full dataset contains **16,708 matches** (75MB zipped, ~500MB unzipped).

### How to get the full dataset:

**Option 1: Download from Cricsheet**
`ash

# Download from official source

curl -o cricsheet_all_male_json.zip https://cricsheet.org/downloads/all_male_json.zip
unzip cricsheet_all_male_json.zip -d cricsheet/
`

**Option 2: Copy from local (if you have it)**
`powershell

# Windows - copy from CricketDataAnalysis project

Copy-Item "C:\Users\amanm\OneDrive\Python Projects\CricketDataAnalysis\all_male_json\*" ".\cricsheet\" -Recurse
`

## Data Structure

Each JSON file represents one match with:

- Match metadata (teams, venue, date, result)
- Ball-by-ball delivery data
- Player information
- Outcome details

See ../docs/VISION.md for detailed data analysis.
