from ..fixtures.buffers import str_buff
import tools.junit_to_markdown.convert as report

import xml.etree.ElementTree as ET




def test_print_element(str_buff):
    """Ensure printed elements match expected result"""

    input_xml = """
    <failure message="This is an example attr">
        This is example content.
    </failure>"""

    expected_result = """<pre>
message: This is an example attr
text: 
This is example content.
</pre>
"""

    root = ET.fromstring(input_xml)

    report.print_element(root, str_buff)

    str_buff.seek(0)
    result = str_buff.read()

    assert result == expected_result



def test_get_chart_data_order():
    """Ensure chart wedges are ordered correctly"""

    input_xml = """
    <testsuite name="pytest" errors="3" failures="3" skipped="1" tests="10">
        This is example content.
    </testsuite>

    """

    # fmt: off
    #    name,      value,  colour,         default_order
    expected_result = [
        ('pass',    3,      '#0f0',         4), 
        ('error',   3,      '#fa0',         2), 
        ('failed',  3,      '#f00',         1), 
        ('skipped', 1,      '#ff0',         3)
         ]
    # fmt: on

    root = ET.fromstring(input_xml)

    result = report.get_chart_data(root)
    assert result == expected_result


def test_get_chart_data_removal():
    """Ensure zero width chart wedges are removed"""

    input_xml = """
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="10"></testsuite>
    """

    # fmt: off
    #    name,      value,  colour,         default_order
    expected_result = [
        ('pass',    10,      '#0f0',         4), 
         ]
    # fmt: on

    root = ET.fromstring(input_xml)

    result = report.get_chart_data(root)
    assert result == expected_result


def test_get_testcase_status_not_pass():
    """Test correct status icon selection"""

    for status, expected_result in report.STATUS_ICONS.items():

        input_xml = f"""
        <testcase><{status}></{status}></testcase>
        """

        root = ET.fromstring(input_xml)
        result = report.get_testcase_status(root)

        assert result == expected_result

def test_get_testcase_status_default():
    """Test default status icon selection"""

    input_xml = f"""
    <testcase></testcase>
    """

    root = ET.fromstring(input_xml)
    result = report.get_testcase_status(root)

    assert result == report.DEFAULT_STATUS_ICON


def test_print_header(str_buff):
    """Ensure header is printed correctly"""

    input_xml = """
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="10"></testsuite>
    """

    root = ET.fromstring(input_xml)
    report.print_header(root, str_buff)
    str_buff.seek(0)
    result = str_buff.read()

    result_split = result.split()

    assert "#" == result_split[0], "result is not formatted as a level 1 header"
    assert ":white_check_mark:" in result_split, "result is missing icon"
    assert "pytest" in result_split, "result is missing name"


def print_testsuite_report(str_buff):

    input_xml = """
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="2">
    <testcase classname="hello.world" name="foo"></testcase>
    <testcase classname="hello.world" name="bar">
        <failure></failure>
        </testcase>
    </testsuite>
    """

    root = ET.fromstring(input_xml)
    report.print_header(root, str_buff)
    str_buff.seek(0)
    result = str_buff.read()
    result_lines = result.splitlines()

    assert "pytest" in result_lines[0], "result is missing header"
    assert any("```mermaid" in line for line in result_lines), "result is missing chart"

    # this may change if <details> is used for any other purpose than testcases  
    assert sum("<details>" in line for line in result_lines) == 2, "result has incorrect testcase test count"

