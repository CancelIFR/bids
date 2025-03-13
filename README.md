# Pilot Pairing Extractor

This script extracts pilot pairings from a PBS (Preferential Bidding System) PDF document and exports them to a CSV file for analysis.

## Features

- Multithreaded processing for faster extraction
- Filter by aircraft type/bid status (737, 777, 787, 320)
- Specify page ranges for extraction
- Extract sequence start dates
- Separate local and base times for departure
- Correctly identify trip duration and duty periods
- Export to CSV for easy analysis

## Requirements

- Python 3.6+
- pdfplumber library

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script with the path to your PDF file:

```bash
python extract_pairings.py PBS_DFW_April_2025_20250307152846.pdf
```

By default, the script:
- Starts extraction from page 7
- Processes all pages in the PDF
- Uses 4 worker threads for parallel processing
- Outputs to a file named `pairings.csv` in the current directory

### Command-line Options

- `--output` or `-o`: Specify a different output file path
- `--start-page` or `-p`: Specify a different starting page (1-indexed)
- `--end-page` or `-e`: Specify the last page to process (1-indexed, inclusive)
- `--aircraft` or `-a`: Filter by aircraft type/bid status (737, 777, 787, 320)
- `--threads` or `-t`: Number of worker threads to use for parallel processing (default: 4)

### Examples

Extract all 777 pairings:
```bash
python extract_pairings.py PBS_DFW_April_2025_20250307152846.pdf --aircraft 777
```

Extract 737 pairings from pages 10-50 with 8 threads:
```bash
python extract_pairings.py PBS_DFW_April_2025_20250307152846.pdf --aircraft 737 --start-page 10 --end-page 50 --threads 8 --output 737_pairings.csv
```

## Performance

The script uses multithreading to process multiple pages in parallel, which significantly improves performance. You can adjust the number of worker threads with the `--threads` option to match your system's capabilities.

## Customization

The script uses regular expression patterns to extract pairing data. If the extraction doesn't work correctly, you may need to adjust the patterns in the `process_page` function to match the format of your PDF.

## Output

The CSV file will contain columns for:
- Sequence: The sequence number of the pairing
- Days: Number of days the pairing spans (from the sequence header)
- Duty_Periods: Number of duty periods in the pairing (from the DP field)
- Position: Crew positions (e.g., CA/FO for Captain/First Officer)
- Start_Date: The date when the sequence starts (MM/DD format)
- Report_Local: Report time in local time
- Flight: Flight number
- Origin: Origin airport code
- Departure_Local: Departure time in local time
- Departure_Base: Departure time in base time
- Meal: Meal code (L for lunch, D for dinner)
- Destination: Destination airport code
- Arrival_Local: Arrival time in local time
- Block: Block time (flight time)
- Release_Local: Release time in local time
- Credit: Credit time for the leg
- Duty: Duty time for the leg
- Layover_City: Layover city code
- Layover_Hotel: Layover hotel name
- Layover_Duration: Duration of the layover
- Aircraft_Type: The aircraft type (e.g., 777, 737, 787, 320)

## Analysis

Once you have the CSV file, you can use tools like Excel, Google Sheets, or Python libraries like pandas to analyze the data for bidding strategies. Some common analyses include:

- Finding pairings with the highest credit to duty ratio
- Identifying pairings with layovers in preferred destinations
- Analyzing block times and duty times
- Finding pairings that fit specific schedule preferences
- Filtering pairings by start date to match your availability
- Comparing local vs. base times for better schedule planning
- Analyzing pairings by number of duty periods 