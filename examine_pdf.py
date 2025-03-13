#!/usr/bin/env python3
"""
Script to examine page 7 of the PBS PDF to understand the format.
"""

import pdfplumber

def examine_pdf(pdf_path, page_num=7):
    """
    Examine a specific page of the PDF and print its text.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to examine (1-indexed)
    """
    print(f"Examining page {page_num} of {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        # Adjust for 0-indexed pages in pdfplumber
        page_idx = page_num - 1
        
        if page_idx >= len(pdf.pages):
            print(f"Error: PDF only has {len(pdf.pages)} pages")
            return
        
        page = pdf.pages[page_idx]
        text = page.extract_text()
        
        print("\n" + "="*80)
        print(f"TEXT FROM PAGE {page_num}:")
        print("="*80)
        print(text)
        print("="*80)
        
        # Also print a sample of the first few lines to help with regex pattern
        print("\nSAMPLE LINES FOR PATTERN MATCHING:")
        print("-"*80)
        lines = text.split('\n')
        for i, line in enumerate(lines[:20]):  # Print first 20 lines
            print(f"Line {i+1}: {line}")

if __name__ == "__main__":
    examine_pdf("PBS_DFW_April_2025_20250307152846.pdf") 