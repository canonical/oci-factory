#! /bin/env python3
import xml.etree.ElementTree as ET
import json

"""
Generate markdown from a JUnit XML report for $GITHUB_STEP_SUMMARY 
"""


def print_element(element, output=None):
    """Generically display attrs and text of a element"""
    print(f"<pre>", file=output)

    for key, value in element.attrib.items():
        print(f"{key}: {value}", file=output)

    if element.text is not None:
        if content := element.text.strip():
            print(f"text: \n{content}", file=output)

    print(f"</pre>", file=output)


def print_testsuite_pie_chart(testsuite, output=None):
    """Generate a pie chart showing test status from testsuite element"""

    failed_tests = int(testsuite.attrib.get("failures", 0))
    error_tests = int(testsuite.attrib.get("errors", 0))
    skipped_tests = int(testsuite.attrib.get("skipped", 0))
    total_tests = int(testsuite.attrib.get("tests", 0))

    # passed test has to be inferred
    pass_tests = total_tests - failed_tests - error_tests - skipped_tests

    #   name,       value,          colour,     default_order
    chart_data = [
        ("failed", failed_tests, "#f00", 1),
        ("error", error_tests, "#fa0", 2),
        ("skipped", skipped_tests, "#ff0", 3),
        ("pass", pass_tests, "#0f0", 4),
    ]
    # note: default_order ensure color match if two wedges have the exact same value

    # filter out wedges with 0 width
    chart_data = list(filter(lambda w: w[1] != 0, chart_data))

    # sort by value, then default order so colors match what we expect
    chart_data = list(sorted(chart_data, key=lambda w: (w[1], w[3]), reverse=True))

    # create a theme
    theme_dict = {
        "theme": "base",
        "themeVariables": {f"pie{n+1}": w[2] for n, w in enumerate(chart_data)},
    }

    ## begin printing pie chart
    print("```mermaid", file=output)

    # theme colors in order: pass, failed, error, skipped
    # Note: init cannot be in quotes
    print(f"%%{{init:{json.dumps(theme_dict)}}}%%", file=output)

    print(f"pie", file=output)
    for key, value, _, _ in chart_data:
        print(f'"{key}" : {value}', file=output)

    print("```", file=output)


def get_testcase_status(testcase):
    """Get status for individual testcase element status"""

    if testcase.find("failure") is not None:
        return ":x:"
    elif testcase.find("error") is not None:
        return ":warning:"
    elif testcase.find("skipped") is not None:
        return ":information_source:"
    else:  # passed
        return ":white_check_mark:"


def print_header(testsuite, output=None):
    """Print a header for the summary"""
    passed = testsuite.attrib.get("failures") == "0" \
                and testsuite.attrib.get("errors") == "0"
    status = ":white_check_mark:" if passed else ":x:"

    print(f"# {status} {testsuite.attrib['name']}", file=output)


def print_testsuite_report(testsuite, output=None):
    """Print complete testsuite element Report"""

    print_header(testsuite, output)

    # use pie chart header as title
    print_testsuite_pie_chart(testsuite, output)

    # print testsuite info
    print_element(testsuite, output)

    # print each test case in collapsable section
    for testcase in testsuite.findall("testcase"):

        print("<details>", file=output)
        
        test_status = get_testcase_status(testcase)
        test_name = (
            testcase.attrib["name"].replace("_", " ").title()
        )  # make the title look better
        test_class = testcase.attrib["classname"]
        print(
            f"<summary>{test_status} {test_name} - {test_class}</summary>", file=output
        )

        for child in testcase.iter():
            print(f"<i>{child.tag}</i>", file=output)
            print_element(child, output)

        print("</details>", file=output)


def print_junit_report(root, output=None):

    for testsuite in root.findall("testsuite"):
        print_testsuite_report(testsuite, output)


if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-junit", help="Path to JUnit XML Report", required=True, type=str
    )

    args = parser.parse_args()

    tree = ET.parse(args.input_junit)
    root = tree.getroot()
    print_junit_report(root, sys.stdout)
