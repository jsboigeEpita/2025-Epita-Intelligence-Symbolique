import json
import os
from collections import Counter
from datetime import datetime

def aggregate_commit_data(input_directory, output_file, limit=215):
    """
    Reads a specified number of commit audit JSON files from a directory,
    aggregates their data, and saves it to a single JSON file.
    """
    commit_data = []
    if not os.path.exists(input_directory):
        print(f"Error: The directory '{input_directory}' was not found.")
        return
        
    files = sorted([f for f in os.listdir(input_directory) if f.endswith('.json')])
    files_to_process = files[:limit]
    
    print(f"Found {len(files)} JSON files. Processing the first {len(files_to_process)}.")

    for filename in files_to_process:
        filepath = os.path.join(input_directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                commit_data.append(data)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {filename}")
        except Exception as e:
            print(f"Error reading file {filename}: {e}")

    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(commit_data, f, indent=4)
        
    print(f"Successfully aggregated data from {len(commit_data)} files into {output_file}")
    return commit_data

def analyze_aggregated_data(aggregated_data):
    """
    Analyzes the aggregated commit data to extract key metrics.
    """
    num_commits = len(aggregated_data)
    if num_commits == 0:
        return {}

    # Temporal analysis
    dates = [datetime.fromisoformat(commit['date']) for commit in aggregated_data]
    start_date = min(dates).strftime('%Y-%m-%d')
    end_date = max(dates).strftime('%Y-%m-%d')

    # Developer analysis
    authors = [commit['author'] for commit in aggregated_data]
    author_counts = Counter(authors)

    # File analysis
    file_changes = Counter()
    for commit in aggregated_data:
        for file in commit.get('files_changed', []):
            if 'filename' in file:
                file_changes[file['filename']] += 1
            
    # Qualitative analysis
    technical_debt = []
    quality_leaps = []
    for commit in aggregated_data:
        analysis = commit.get('qualitative_analysis', {})
        technical_debt.extend(analysis.get('technical_debt_signals', []))
        quality_leaps.extend(analysis.get('quality_leaps', []))

    analysis_summary = {
        "overview": {
            "total_commits": num_commits,
            "period_start": start_date,
            "period_end": end_date,
            "average_files_changed": sum(len(c.get('files_changed', [])) for c in aggregated_data) / num_commits
        },
        "developer_activity": dict(author_counts.most_common()),
        "file_impact": dict(file_changes.most_common(20)),
        "technical_debt_summary": technical_debt,
        "quality_leaps_summary": quality_leaps
    }
    
    return analysis_summary

if __name__ == '__main__':
    INPUT_DIR = 'docs/commits_audit/'
    AGGREGATED_FILE = 'docs/audit/synthesis_reports/aggregated_commits_1_a_215.json'
    ANALYSIS_FILE = 'docs/audit/synthesis_reports/analysis_summary.json'
    
    # Step 1: Aggregate data
    aggregated_data = aggregate_commit_data(INPUT_DIR, AGGREGATED_FILE)
    
    # Step 2: Analyze data
    if aggregated_data:
        analysis_results = analyze_aggregated_data(aggregated_data)
        
        # Step 3: Save analysis
        with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=4)
        print(f"Successfully saved analysis summary to {ANALYSIS_FILE}")