import argparse
import re
from pathlib import Path
import logging
from typing import List, Dict, Any, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CodeRecovery:
    """
    Analyzes development logs to recover and snapshot code at various stages.
    """

    def __init__(self, output_dir: Path, promising_range: Tuple[int, int]):
        self.output_dir = output_dir
        self.promising_range = promising_range
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Output directory set to: {self.output_dir.resolve()}")

    def process_log_file(self, log_file: Path):
        """
        Processes a single log file to extract and snapshot code states.
        """
        logging.info(f"Processing log file: {log_file.name}")
        content = log_file.read_text(encoding='utf-8')
        log_identifier = log_file.stem

        events = self._collect_events(content)

        file_states: Dict[str, Dict[str, Any]] = {}
        snapshots_created = 0

        for _, event_type, *data in events:
            if event_type == 'code':
                tool_name, xml_content = data
                self._update_file_states(file_states, tool_name, xml_content)
            elif event_type == 'test':
                passed_count, = data
                if self.promising_range[0] <= passed_count <= self.promising_range[1]:
                    snapshots_created += 1
                    snapshot_name = f"{log_identifier}_snapshot_{snapshots_created}_passed_{passed_count}"
                    self._create_snapshot(snapshot_name, file_states)
                    logging.info(f"Created snapshot '{snapshot_name}' for test run with {passed_count} passed tests.")

    def _collect_events(self, content: str) -> List[Tuple[int, str, Any]]:
        """
        Collects and sorts all relevant events (code operations, test summaries) from the log content.
        """
        # Regex for capturing tool usage blocks
        code_block_regex = r"<(?>read_file|write_to_file|apply_diff)>(.*?)</(?>read_file|write_to_file|apply_diff)>"
        # A more specific regex to capture the tool name and content separately
        tool_tag_regex = r"<(?P<tool>read_file|write_to_file|apply_diff)>(?P<xml_content>.*?)</(?P=tool)>"

        # Regex for Pytest summary section
        pytest_summary_regex = r"={5,}\s*short test summary info\s*={5,}[\s\S]*?(?P<passed>\d+)\s+passed"

        code_events = [(m.end(0), 'code', m.group('tool'), m.group('xml_content')) for m in re.finditer(tool_tag_regex, content, re.DOTALL)]
        test_events = [(m.start(0), 'test', int(m.group('passed'))) for m in re.finditer(pytest_summary_regex, content)]

        all_events = sorted(code_events + test_events, key=lambda x: x[0])
        logging.info(f"Collected {len(all_events)} events ({len(code_events)} code, {len(test_events)} test).")
        return all_events
    
    def _extract_path_from_xml(self, xml_content: str) -> Optional[str]:
        """Utility to extract file path from the inner XML of a tool tag."""
        path_match = re.search(r"<path>(.*?)</path>", xml_content, re.DOTALL)
        if path_match:
            return path_match.group(1).strip()
        return None

    def _update_file_states(self, file_states: Dict[str, Dict[str, Any]], tool_name: str, xml_content: str):
        """
        Updates the in-memory state of files based on a code operation event.
        """
        path = self._extract_path_from_xml(xml_content)
        if not path:
            logging.warning(f"Could not find path in {tool_name} block: {xml_content[:100]}...")
            return

        if tool_name in ['read_file', 'write_to_file']:
            content_match = re.search(r"<content>(.*?)</content>", xml_content, re.DOTALL)
            content = content_match.group(1).strip() if content_match else ""
            
            # For read_file, it's the baseline. For write_to_file, it's a full replacement.
            file_states[path] = {
                'baseline_content': content,
                'diffs': [], 
                'last_op': tool_name
            }
            logging.debug(f"State for '{path}' reset by {tool_name}.")

        elif tool_name == 'apply_diff':
            if path in file_states:
                diff_content_match = re.search(r"<diff>(.*?)</diff>", xml_content, re.DOTALL)
                if diff_content_match:
                    diff_content = diff_content_match.group(1)
                    file_states[path]['diffs'].append(diff_content)
                    file_states[path]['last_op'] = tool_name
                    logging.debug(f"Appended diff to '{path}'.")
            else:
                logging.warning(f"Found apply_diff for '{path}' but no prior state. Ignoring.")

    def _create_snapshot(self, name: str, file_states: Dict[str, Dict[str, Any]]):
        """
        Saves the current state of all tracked files to a new snapshot directory.
        """
        snapshot_dir = self.output_dir / name
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        for path_str, state in file_states.items():
            file_path = Path(path_str)
            # Create a safe version of the path for writing to the snapshot dir
            snapshot_file_path = snapshot_dir / file_path.name
            
            # Save the baseline content
            snapshot_file_path.write_text(state['baseline_content'], encoding='utf-8')

            # If there are diffs, save them to a companion file
            if state['diffs']:
                diffs_file_path = snapshot_dir / f"{file_path.name}.diffs"
                all_diffs = "\n\n".join(state['diffs'])
                diffs_file_path.write_text(all_diffs, encoding='utf-8')
                logging.info(f"  - Saved {path_str} with {len(state['diffs'])} diff(s).")
            else:
                logging.info(f"  - Saved {path_str} (baseline only).")


def main():
    parser = argparse.ArgumentParser(description="Recover code from development logs by creating snapshots based on test results.")
    parser.add_argument("log_files", nargs='+', type=Path, help="Path to one or more log files to process.")
    parser.add_argument("--output-dir", type=Path, default=Path("./code_recovery_snapshots"), help="Directory to save the snapshots.")
    parser.add_argument("--promising-range", type=int, nargs=2, default=[5, 7], help="The range of passed tests [min, max] to consider 'promising' for a snapshot.")
    
    args = parser.parse_args()

    if not all(f.exists() for f in args.log_files):
        print("Error: One or more log files do not exist.")
        exit(1)

    recovery = CodeRecovery(args.output_dir, tuple(args.promising_range))
    for log_file in args.log_files:
        recovery.process_log_file(log_file)
    
    print(f"\nProcessing complete. Snapshots saved in: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()