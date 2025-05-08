#!/usr/bin/env python
import argparse
import os
import sys
from dotenv import load_dotenv
from linkedin_decision_maker_extractor import LinkedInDecisionMakerExtractor
from datetime import datetime

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="LinkedIn Decision Maker Extraction Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--company", "-c",
        type=str,
        required=True,
        help="LinkedIn company URL"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="decision_makers",
        help="Output file name prefix (without extension)"
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["csv", "json", "both"],
        default="both",
        help="Output format"
    )
    
    parser.add_argument(
        "--api-key", "-k",
        type=str,
        help="LinkedIn API key (overrides environment variable)"
    )
    
    return parser.parse_args()

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Get API key from arguments or environment variable
    api_key = args.api_key or os.getenv("LINKEDIN_API_KEY")
    
    if not api_key:
        print("Error: LinkedIn API key not provided. Use --api-key option or set LINKEDIN_API_KEY environment variable.")
        sys.exit(1)
    
    # Initialize the extractor
    extractor = LinkedInDecisionMakerExtractor(api_key)
    
    # Extract decision makers
    print(f"Extracting decision makers from {args.company}...")
    decision_makers = extractor.extract_decision_makers(args.company)
    
    if not decision_makers:
        print("No decision makers found.")
        sys.exit(0)
    
    print(f"Found {len(decision_makers)} decision makers.")
    
    # Generate output file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = f"{args.output}_{timestamp}"
    
    # Save results based on format option
    if args.format in ["csv", "both"]:
        csv_file = f"{output_base}.csv"
        extractor.save_to_csv(decision_makers, csv_file)
        print(f"Results saved to {csv_file}")
    
    if args.format in ["json", "both"]:
        json_file = f"{output_base}.json"
        extractor.save_to_json(decision_makers, json_file)
        print(f"Results saved to {json_file}")

if __name__ == "__main__":
    main()