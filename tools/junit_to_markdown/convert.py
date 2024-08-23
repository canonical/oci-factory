#! /bin/env python3
import xml.etree.ElementTree as ET
from io import TextIOBase
import json

DEFAULT_STATUS_ICON = ":white_check_mark:"
STATUS_ICONS = {
    "failure": ":x:",
    "error": ":warning:",
    "skipped": ":information_source:",
    "information_source": ":x:",
}


def print_element(element: ET.Element, output: TextIOBase = None):
    """Generically display attrs and text of a element"""
    print(f"<pre>", file=output)

    for key, value in element.attrib.items():
        print(f"{key}: {value}", file=output)

    if element.text is not None:
        if content := element.text.strip():
            print(f"text: \n{content}", file=output)

    print(f"</pre>", file=output)

def get_chart_data(testsuite: ET.Element):
    """Extract and order data used in pie chart"""

    failed_tests = int(testsuite.attrib.get("failures", 0))
    error_tests = int(testsuite.attrib.get("errors", 0))
    skipped_tests = int(testsuite.attrib.get("skipped", 0))
    total_tests = int(testsuite.attrib.get("tests", 0))

    # passed test has to be inferred
    pass_tests = total_tests - failed_tests - error_tests - skipped_tests

    # disable black autoformatter for a moment 
    # fmt: off

    #    name,      value,          colour,     default_order
    chart_data = [
        ("failed",  failed_tests,   "#f00",     1),
        ("error",   error_tests,    "#fa0",     2),
        ("skipped", skipped_tests,  "#ff0",     3),
        ("pass",    pass_tests,     "#0f0",     4),
    ]
    # note: default_order ensures color match if two wedges have the exact same value
    # fmt: on

    # filter out wedges with 0 width
    chart_data = list(filter(lambda w: w[1] != 0, chart_data))

    # sort by value, then default order so colors match what we expect
    chart_data = list(sorted(chart_data, key=lambda w: (w[1], w[3]), reverse=True))

    return chart_data

def print_testsuite_pie_chart(testsuite: ET.Element, output: TextIOBase = None):
    """Generate a pie chart showing test status from testsuite element"""

    chart_data = get_chart_data(testsuite)

    # create the chart theme
    theme_dict = {
        "theme": "base",
        "themeVariables": {f"pie{n+1}": w[2] for n, w in enumerate(chart_data)},
    }

    # begin printing pie chart...
    print("```mermaid", file=output)

    # theme colors in order: pass, failed, error, skipped
    # Note: init cannot be in quotes
    print(f"%%{{init:{json.dumps(theme_dict)}}}%%", file=output)

    print(f"pie", file=output)
    for key, value, _, _ in chart_data:
        print(f'"{key}" : {value}', file=output)

    print("```", file=output)


def get_testcase_status(testcase: ET.Element):
    """Get status for individual testcase elements"""

    for key, value in STATUS_ICONS.items():
        if testcase.find(key) is not None:
            return value

    return DEFAULT_STATUS_ICON


def print_header(testsuite: ET.Element, output: TextIOBase = None):
    """Print a header for the summary"""
    passed = (
        testsuite.attrib.get("failures") == "0"
        and testsuite.attrib.get("errors") == "0"
    )
    status = ":white_check_mark:" if passed else ":x:"
    name = testsuite.attrib["name"]

    print(f"# {status} {name}", file=output)


def print_testsuite_report(testsuite: ET.Element, output: TextIOBase = None):
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


def print_junit_report(root: ET.Element, output: TextIOBase = None):
    """Print report by iterating over all <testsuite> elements in root"""

    for testsuite in root.findall("testsuite"):
        print_testsuite_report(testsuite, output)
