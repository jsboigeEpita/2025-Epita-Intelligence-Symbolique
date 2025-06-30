

import argparse
from fallacy_pipeline import run_fallacy_pipeline

def main():
    parser = argparse.ArgumentParser(description="Run the French Fallacy Detection Pipeline on a given text.")
    parser.add_argument("text", type=str, help="The French text argument to analyze for fallacies.")
    
    args = parser.parse_args()
    
    print(f"\nAnalyzing the provided text: '{args.text}'\n")
    run_fallacy_pipeline(args.text)

if __name__ == '__main__':
    main()

