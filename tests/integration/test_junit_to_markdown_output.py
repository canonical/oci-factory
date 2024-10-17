from ..fixtures.buffers import str_buff
from ..fixtures.sample_data import junit_with_failure
import tools.junit_to_markdown.convert as report


def test_print_redirection(junit_with_failure, str_buff, capsys):
    """Ensure that the report is entirely redirected when needed"""

    report.print_junit_report(junit_with_failure, str_buff)
    report.print_junit_report(junit_with_failure, None)  # print report to stdout

    str_buff.seek(0)
    str_buff_content = str_buff.read()

    captured = capsys.readouterr()
    stdout_content = captured.out

    assert stdout_content == str_buff_content, "Printing to multiple locations."
