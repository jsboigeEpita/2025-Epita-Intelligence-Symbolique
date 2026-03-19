import json
import argparse

def extract_commits_by_index(input_file, start_index, end_index, output_file):
    """
    Extracts commits from a JSON file based on a given index range and saves them to a new file.

    :param input_file: Path to the input JSON file with indexed commits.
    :param start_index: The starting index of the range (inclusive).
    :param end_index: The ending index of the range (inclusive).
    :param output_file: Path to the output JSON file.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            all_commits = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {input_file} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file}.")
        return

    # Filter commits based on the index range
    extracted_commits = [
        commit for commit in all_commits 
        if start_index <= commit.get('index', -1) <= end_index
    ]

    # Save the extracted commits to the output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_commits, f, indent=4, ensure_ascii=False)
        print(f"Successfully extracted {len(extracted_commits)} commits to {output_file}")
    except IOError as e:
        print(f"Error writing to {output_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract a range of commits from a JSON file based on their index."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input JSON file (e.g., aggregated_commits_1_a_215.json)"
    )
    parser.add_argument(
        "start_index",
        type=int,
        help="The starting commit index (inclusive)."
    )
    parser.add_argument(
        "end_index",
        type=int,
        help="The ending commit index (inclusive)."
    )
    parser.add_argument(
        "output_file",
        help="Path to the output file where extracted commits will be saved."
    )

    args = parser.parse_args()

    extract_commits_by_index(args.input_file, args.start_index, args.end_index, args.output_file)