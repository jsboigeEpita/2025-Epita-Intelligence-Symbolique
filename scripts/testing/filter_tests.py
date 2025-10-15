import argparse


def filter_tests(input_file, output_file, keywords):
    """
    Filters tests from an input file based on a list of keywords and writes the result to an output file.
    """
    with open(input_file, "r", encoding="utf-8") as f_in, open(
        output_file, "w", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            if not any(keyword in line for keyword in keywords):
                f_out.write(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter a list of tests based on keywords."
    )
    parser.add_argument(
        "--input", required=True, help="Input file with the list of tests."
    )
    parser.add_argument(
        "--output", required=True, help="Output file for the filtered list of tests."
    )
    parser.add_argument(
        "--keywords", nargs="+", required=True, help="Keywords to filter out."
    )
    args = parser.parse_args()

    filter_tests(args.input, args.output, args.keywords)
