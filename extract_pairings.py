#!/usr/bin/env python3
"""
Script to extract pilot pairings from a PBS PDF document and export to CSV.
This script extracts data starting from page 7 of the PDF.
"""

import re
import csv
import argparse
import concurrent.futures
import multiprocessing
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
try:
    import pdfplumber
except ImportError:
    print("Please install pdfplumber: pip install pdfplumber")
    exit(1)

def process_page_text(page_text: str, page_num: int) -> List[List[str]]:
    """
    Process the text content of a single page and extract pairings.
    
    Args:
        page_text: The extracted text from the page
        page_num: Page number for logging purposes
        
    Returns:
        List of extracted pairings from this page
    """
    page_pairings = []
    
    # Skip if no text found
    if not page_text:
        return []
    
    # Split text into lines
    lines = page_text.split('\n')
    
    # Initialize all variables to track current pairing
    current_seq = None
    current_days = None
    duty_periods = None
    current_position = None
    current_special = None
    report_time_local = None
    report_time_base = None
    aircraft_type = None
    leg_num = None
    flight = None
    origin = None
    departure_local = None
    departure_base = None
    meal = None
    destination = None
    arrival_local = None
    arrival_base = None
    block = None
    release_time_local = None
    release_time_base = None
    credit = None
    duty = None
    layover_city = None
    layover_hotel = None
    layover_duration = None
    start_dates = []  # List to store the start dates for the sequence
    month = "04"  # Default month (April)
    
    # Compile regex patterns once for better performance
    dp_pattern = re.compile(r'DP\s+D/A')
    calendar_pattern = re.compile(r'CALENDAR\s+(\d{2})/\d{2}')
    aircraft_pattern = re.compile(r'DFW\s+(\d{3})')
    seq_pattern = re.compile(r'SEQ\s+(\d+)\s+(\d+)\s+OPS\s+POSN\s+([A-Z]+)\s+([A-Z]+)(?:\s+(.+))?')
    rpt_pattern = re.compile(r'RPT\s+(\d{4})/(\d{4})(?:\s+(.+))?')
    date_line_pattern = re.compile(r'^(?:\s*\d{1,2}\s*)+$')
    date_numbers_pattern = re.compile(r'\b(\d{1,2})\b')
    leg_pattern = re.compile(r'(\d+)\s+(\d+)/(\d+)\s+(\d+)\s+(\d+)\s+([A-Z]{3})\s+(\d{4})/(\d{4})\s+([LD])\s+([A-Z]{3})\s+(\d{4})/(\d{4})\s+(\d+\.\d+)(?:\s+(.+))?')
    rls_pattern = re.compile(r'RLS\s+(\d{4})/(\d{4})\s+(\d+\.\d+)\s+\d+\.\d+\s+\d+\.\d+\s+(\d+\.\d+)(?:\s+(.+))?')
    layover_pattern = re.compile(r'([A-Z]{3})\s+(.*?)(?:\s+\d+)?\s+(\d+\.\d+)(?:\s+(.+))?')
    
    # Process each line
    for line in lines:
        # Skip header and separator lines
        if (line.startswith("DAY") or line.startswith("---") or 
            "COCKPIT ISSUED" in line or len(line.strip()) < 5):  # Skip very short lines
            continue
        
        # Check for DP (Duty Periods) in header
        dp_match = dp_pattern.search(line)
        if dp_match:
            continue
        
        # Check for calendar month in header (e.g., "CALENDAR 04/01−05/01")
        calendar_match = calendar_pattern.search(line)
        if calendar_match:
            month = calendar_match.group(1)
            continue
        
        # Check for aircraft type line (e.g., "DFW 777")
        aircraft_match = aircraft_pattern.match(line)
        if aircraft_match:
            aircraft_type = aircraft_match.group(1)
            continue
        
        # Check if this is a new sequence line
        # Format: SEQ 182 30 OPS POSN CA FO KOREAN OPERATION
        # Where 182 is the sequence number and 30 is the number of days
        seq_match = seq_pattern.match(line)
        if seq_match:
            current_seq = seq_match.group(1)
            current_days = seq_match.group(2)  # This is actually the number of days
            current_position = f"{seq_match.group(3)}/{seq_match.group(4)}"
            current_special = seq_match.group(5) if len(seq_match.groups()) > 4 and seq_match.group(5) else ""
            start_dates = []  # Reset start dates for new sequence
            
            # Reset duty periods for new sequence
            duty_periods = None
            continue
        
        # Check if this is a report time line with dates
        # Format: RPT 0915/0915 −− 2 3 4 5 6
        rpt_match = rpt_pattern.match(line)
        if rpt_match and current_seq:
            report_time_local = rpt_match.group(1)
            report_time_base = rpt_match.group(2)
            # Check if there are dates on this line
            if len(rpt_match.groups()) > 2 and rpt_match.group(3):
                date_part = rpt_match.group(3)
                # Extract dates (numbers) from this line
                date_numbers = date_numbers_pattern.findall(date_part)
                start_dates.extend([f"{month}/{d.zfill(2)}" for d in date_numbers if d.isdigit()])
            continue
        
        # Check for date numbers in other lines (e.g., "7 8 9 10 11 12 13")
        # Only check if we're in a sequence and don't have dates yet
        if current_seq and not start_dates:
            # Look for lines with just numbers separated by spaces
            date_line_match = date_line_pattern.match(line.strip())
            if date_line_match:
                date_numbers = date_numbers_pattern.findall(line)
                start_dates.extend([f"{month}/{d.zfill(2)}" for d in date_numbers if d.isdigit()])
                continue
        
        # Check if this is a flight leg line
        # Format: 1 1/2 83 281 DFW 1015/1015 L ICN 1530/0130 15.15
        leg_match = leg_pattern.match(line)
        if leg_match and current_seq:
            leg_num = leg_match.group(1)
            
            # Extract duty periods from the leg line (e.g., "1/2" means 2 duty periods)
            dp_current = leg_match.group(2)
            dp_total = leg_match.group(3)
            if duty_periods is None:
                duty_periods = dp_total  # Set duty periods from the first leg
            
            flight = leg_match.group(5)
            origin = leg_match.group(6)
            departure_local = leg_match.group(7)
            departure_base = leg_match.group(8)
            meal = leg_match.group(9)
            destination = leg_match.group(10)
            arrival_local = leg_match.group(11)
            arrival_base = leg_match.group(12)
            block = leg_match.group(13)
            
            # Check if there are dates on this line
            if len(leg_match.groups()) > 13 and leg_match.group(14):
                date_part = leg_match.group(14)
                # Extract dates (numbers) from this line
                date_numbers = date_numbers_pattern.findall(date_part)
                if not start_dates:  # Only add if we don't have dates yet
                    start_dates.extend([f"{month}/{d.zfill(2)}" for d in date_numbers if d.isdigit()])
            continue
        
        # Check if this is a release time line
        # Format: RLS 1600/0200 15.15 0.00 15.15 16.45 16.15
        rls_match = rls_pattern.match(line)
        if rls_match and current_seq:
            release_time_local = rls_match.group(1)
            release_time_base = rls_match.group(2)
            credit = rls_match.group(3)
            duty = rls_match.group(4)
            
            # Check if there are dates on this line
            if len(rls_match.groups()) > 4 and rls_match.group(5):
                date_part = rls_match.group(5)
                # Extract dates (numbers) from this line
                date_numbers = date_numbers_pattern.findall(date_part)
                if not start_dates:  # Only add if we don't have dates yet
                    start_dates.extend([f"{month}/{d.zfill(2)}" for d in date_numbers if d.isdigit()])
            continue
        
        # Check if this is a layover hotel line
        # Format: ICN SHERATON INCHEON 82328351000 24.25
        layover_match = layover_pattern.match(line)
        if layover_match and current_seq:
            layover_city = layover_match.group(1)
            layover_hotel = layover_match.group(2).strip()
            layover_duration = layover_match.group(3)
            
            # Check if there are dates on this line
            if len(layover_match.groups()) > 3 and layover_match.group(4):
                date_part = layover_match.group(4)
                # Extract dates (numbers) from this line
                date_numbers = date_numbers_pattern.findall(date_part)
                if not start_dates:  # Only add if we don't have dates yet
                    start_dates.extend([f"{month}/{d.zfill(2)}" for d in date_numbers if d.isdigit()])
            
            # Only add the pairing if we have all the necessary data
            if (flight and origin and destination and 
                departure_local and arrival_local and block and credit and duty):
                
                # Get the start date (first date in the list, or empty string if none)
                start_date = start_dates[0] if start_dates else ""
                
                # Add the pairing to our list
                pairing = [
                    current_seq, current_days, duty_periods, current_position, 
                    start_date, 
                    report_time_local, 
                    flight, origin, 
                    departure_local, departure_base, meal,
                    destination, 
                    arrival_local, block, 
                    release_time_local, 
                    credit, duty,
                    layover_city, layover_hotel, layover_duration, aircraft_type
                ]
                page_pairings.append(pairing)
            continue
    
    return page_pairings

def extract_page_text(pdf_path: str, page_num: int) -> str:
    """
    Extract text from a single page of the PDF.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to process (1-indexed)
        
    Returns:
        Extracted text from the page
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Adjust for 0-indexed pages in pdfplumber
            page_idx = page_num - 1
            
            if page_idx >= len(pdf.pages):
                return ""
            
            page = pdf.pages[page_idx]
            return page.extract_text()
    except Exception as e:
        print(f"Error extracting text from page {page_num}: {e}")
        return ""

def process_page_batch(pdf_path: str, page_nums: List[int], aircraft_type: Optional[str] = None) -> List[List[str]]:
    """
    Process a batch of pages from the PDF.
    
    Args:
        pdf_path: Path to the PDF file
        page_nums: List of page numbers to process (1-indexed)
        aircraft_type: Filter by aircraft type
        
    Returns:
        List of extracted pairings from these pages
    """
    batch_pairings = []
    
    for page_num in page_nums:
        try:
            # Extract text from the page
            page_text = extract_page_text(pdf_path, page_num)
            
            # Process the page text
            page_pairings = process_page_text(page_text, page_num)
            
            # Filter by aircraft type if specified
            if aircraft_type:
                page_pairings = [p for p in page_pairings if p[-1] == aircraft_type]
                
            batch_pairings.extend(page_pairings)
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
    
    return batch_pairings

def extract_pairings(pdf_path: str, output_csv: str, start_page: int = 7, 
                    end_page: Optional[int] = None, aircraft_type: Optional[str] = None,
                    max_workers: int = 4) -> int:
    """
    Extract pilot pairings from the PDF and save to CSV.
    
    Args:
        pdf_path: Path to the PDF file
        output_csv: Path to save the CSV output
        start_page: Page to start extraction from (1-indexed)
        end_page: Page to end extraction at (1-indexed, inclusive), or None for all pages
        aircraft_type: Filter by aircraft type (e.g., '777', '737', '787', '320')
        max_workers: Maximum number of worker processes to use
        
    Returns:
        Number of pairings extracted
    """
    print(f"Extracting pairings from {pdf_path}, starting at page {start_page}")
    if end_page:
        print(f"Will stop at page {end_page}")
    if aircraft_type:
        print(f"Filtering for aircraft type: {aircraft_type}")
    
    # List to store all extracted pairings
    all_pairings = []
    
    # Column headers for the CSV
    headers = [
        "Sequence", "Days", "Duty_Periods", "Position", 
        "Start_Date", 
        "Report_Local", 
        "Flight", "Origin", 
        "Departure_Local", "Departure_Base", "Meal", 
        "Destination", 
        "Arrival_Local", "Block", 
        "Release_Local", 
        "Credit", "Duty", 
        "Layover_City", "Layover_Hotel", "Layover_Duration", "Aircraft_Type"
    ]
    
    # Determine the range of pages to process
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if end_page:
            end_page = min(end_page, total_pages)
        else:
            end_page = total_pages
    
    # Create a list of page numbers to process
    page_numbers = list(range(start_page, end_page + 1))
    total_pages_to_process = len(page_numbers)
    
    # Determine optimal batch size based on number of workers
    # Aim for at least 2 batches per worker for better load balancing
    batch_size = max(1, math.ceil(total_pages_to_process / (max_workers * 2)))
    
    # Create batches of pages
    batches = [page_numbers[i:i+batch_size] for i in range(0, len(page_numbers), batch_size)]
    
    print(f"Processing {total_pages_to_process} pages with {max_workers} worker processes...")
    print(f"Pages divided into {len(batches)} batches of ~{batch_size} pages each")
    
    # Use multiprocessing instead of threading to bypass the GIL
    # This is more efficient for CPU-bound tasks like regex processing
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Create a dictionary to store future: batch for progress tracking
        future_to_batch = {
            executor.submit(process_page_batch, pdf_path, batch, aircraft_type): batch
            for batch in batches
        }
        
        # Process completed futures as they come in
        completed_pages = 0
        for future in concurrent.futures.as_completed(future_to_batch):
            batch = future_to_batch[future]
            try:
                batch_pairings = future.result()
                all_pairings.extend(batch_pairings)
                
                # Update progress
                completed_pages += len(batch)
                if completed_pages >= total_pages_to_process:
                    completed_pages = total_pages_to_process  # Cap at 100%
                
                print(f"Processed ~{completed_pages}/{total_pages_to_process} pages ({completed_pages/total_pages_to_process:.1%})")
            except Exception as e:
                print(f"Error processing batch {batch}: {e}")
    
    # Write to CSV
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(all_pairings)
    
    print(f"Extracted {len(all_pairings)} pairings to {output_csv}")
    return len(all_pairings)

def main():
    parser = argparse.ArgumentParser(description='Extract pilot pairings from PBS PDF')
    parser.add_argument('pdf_file', help='Path to the PBS PDF file')
    parser.add_argument('--output', '-o', default='pairings.csv', help='Output CSV file path')
    parser.add_argument('--start-page', '-p', type=int, default=7, help='Page to start extraction from (1-indexed)')
    parser.add_argument('--end-page', '-e', type=int, help='Page to end extraction at (1-indexed, inclusive)')
    parser.add_argument('--aircraft', '-a', choices=['737', '777', '787', '320'], 
                        help='Filter by aircraft type/bid status (737, 777, 787, 320)')
    parser.add_argument('--threads', '-t', type=int, default=4, 
                        help='Number of worker processes to use (default: 4)')
    
    args = parser.parse_args()
    
    # Validate input file exists
    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: File {pdf_path} does not exist")
        return 1
    
    # Set a reasonable maximum for worker processes
    max_workers = min(args.threads, multiprocessing.cpu_count())
    
    # Extract pairings
    num_pairings = extract_pairings(
        pdf_path, 
        args.output, 
        args.start_page, 
        args.end_page, 
        args.aircraft,
        max_workers
    )
    
    if num_pairings > 0:
        print(f"Successfully extracted {num_pairings} pairings")
        return 0
    else:
        print("No pairings were extracted. Check the PDF format and extraction pattern.")
        return 1

if __name__ == "__main__":
    # Ensure proper multiprocessing behavior on all platforms
    multiprocessing.freeze_support()
    exit(main()) 