import argparse, sys
import xml.etree.ElementTree as ET
from .convert import print_junit_report


parser = argparse.ArgumentParser(
    description="Generate markdown from a JUnit XML report for $GITHUB_STEP_SUMMARY"
)

parser.add_argument(
    "--input-junit", help="Path to JUnit XML Report", required=True, type=str
)


def main():
    args = parser.parse_args()

    tree = ET.parse(args.input_junit)
    root = tree.getroot()

    print_junit_report(root, sys.stdout)


if __name__ == "__main__":
    main()
