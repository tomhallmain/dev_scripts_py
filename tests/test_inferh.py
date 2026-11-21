"""``ds inferh``: the reference cases from ``dev_scripts/tests/t_infer.sh``.

Separators are given explicitly: those cases depend only on the header scoring, and the
separator the original infers for them is a comma (or ``|`` where the test sets it).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.infer_headers import has_header, header_score, split_row

DATA = Path(__file__).resolve().parent / "data"

INLINE_CASES = [
    pytest.param('FirstName,LastName,PhoneNumber,Email,Department\nJohn,Doe,123-456-7890,john.doe@email.com,Engineering\nJane,Smith,234-567-8901,jane.smith@email.com,Marketing\nBob,Johnson,345-678-9012,bob.johnson@email.com,Sales\nAlice,Williams,456-789-0123,alice.williams@email.com,HR\nCharlie,Brown,567-890-1234,charlie.brown@email.com,Finance\nDavid,Miller,678-901-2345,david.miller@email.com,IT\n', ',', True, id='CamelCase headers'),
    pytest.param('first_name,last_name,phone_number,email_address,department_name\nJohn,Doe,123-456-7890,john.doe@email.com,Engineering\nJane,Smith,234-567-8901,jane.smith@email.com,Marketing\nBob,Johnson,345-678-9012,bob.johnson@email.com,Sales\nAlice,Williams,456-789-0123,alice.williams@email.com,HR\nCharlie,Brown,567-890-1234,charlie.brown@email.com,Finance\n', ',', True, id='snake_case headers'),
    pytest.param('FIRST_NAME,LAST_NAME,PHONE_NUMBER,EMAIL_ADDRESS,DEPARTMENT\nJohn,Doe,123-456-7890,john.doe@email.com,Engineering\nJane,Smith,234-567-8901,jane.smith@email.com,Marketing\nBob,Johnson,345-678-9012,bob.johnson@email.com,Sales\nAlice,Williams,456-789-0123,alice.williams@email.com,HR\nCharlie,Brown,567-890-1234,charlie.brown@email.com,Finance\n', ',', True, id='CONSTANT_CASE headers'),
    pytest.param('sum_sales,avg_price,count_items,total_cost,mean_value,median_score\n15000.50,125.99,120,18750.25,156.25,145.00\n22500.75,135.50,167,28875.50,172.90,168.50\n18750.25,115.75,145,21562.80,148.75,142.25\n25000.00,145.25,172,32250.75,187.50,182.75\n19500.50,128.99,152,24375.50,160.35,157.50\n', ',', True, id='statistical headers'),
    pytest.param('date_created,timestamp,modified_at,update_time,creation_date\n2024-01-01,1704067200,2024-01-15T10:30:00Z,1704585600,2024-01-01\n2024-01-02,1704153600,2024-01-16T14:20:00Z,1704672000,2024-01-02\n2024-01-03,1704240000,2024-01-17T09:15:00Z,1704758400,2024-01-03\n2024-01-04,1704326400,2024-01-18T16:45:00Z,1704844800,2024-01-04\n2024-01-05,1704412800,2024-01-19T11:25:00Z,1704931200,2024-01-05\n', ',', True, id='time-related headers'),
    pytest.param('header\nvalue1\nvalue2\nvalue3\nvalue4\nvalue5\nvalue6\n', ',', False, id='single column'),
    pytest.param('1,2,3,4,5\n6,7,8,9,10\n11,12,13,14,15\n16,17,18,19,20\n21,22,23,24,25\n26,27,28,29,30\n', ',', False, id='numeric data'),
    pytest.param('First Name|Last Name|Phone|Email|Department\nJohn|Doe|123-456-7890|john.doe@email.com|Engineering\nJane|Smith|234-567-8901|jane.smith@email.com|Marketing\nBob|Johnson|345-678-9012|bob.johnson@email.com|Sales\nAlice|Williams|456-789-0123|alice.williams@email.com|HR\nCharlie|Brown|567-890-1234|charlie.brown@email.com|Finance\n', '|', True, id='pipe separator'),
    pytest.param('id,config,data,metadata,settings\n1,{"type":"A","value":10},{"name":"test1"},{"status":"active"},{"enabled":true}\n2,{"type":"B","value":20},{"name":"test2"},{"status":"inactive"},{"enabled":false}\n3,{"type":"C","value":30},{"name":"test3"},{"status":"pending"},{"enabled":true}\n4,{"type":"D","value":40},{"name":"test4"},{"status":"active"},{"enabled":true}\n5,{"type":"E","value":50},{"name":"test5"},{"status":"inactive"},{"enabled":false}\n', ',', True, id='JSON fields'),
    pytest.param('id,html_content,xml_data,description,status\n1,<div class="test">content1</div>,<data><value>1</value></data>,Test Entry 1,active\n2,<p style="color:red">content2</p>,<data><value>2</value></data>,Test Entry 2,inactive\n3,<span id="item3">content3</span>,<data><value>3</value></data>,Test Entry 3,pending\n4,<div class="test">content4</div>,<data><value>4</value></data>,Test Entry 4,active\n5,<p style="color:blue">content5</p>,<data><value>5</value></data>,Test Entry 5,inactive\n', ',', True, id='HTML/XML fields'),
    pytest.param('User_ID,firstName,LAST-NAME,Email_Address,phoneNumber\n1,John,Doe,john.doe@email.com,123-456-7890\n2,Jane,Smith,jane.smith@email.com,234-567-8901\n3,Bob,Johnson,bob.johnson@email.com,345-678-9012\n4,Alice,Williams,alice.williams@email.com,456-789-0123\n5,Charlie,Brown,charlie.brown@email.com,567-890-1234\n', ',', True, id='mixed headers'),
    pytest.param('"Column 1","Column 2","Column 3","Column 4","Column 5"\n"value 1.1","value 1.2","value 1.3","value 1.4","value 1.5"\n"value 2.1","value 2.2","value 2.3","value 2.4","value 2.5"\n"value 3.1","value 3.2","value 3.3","value 3.4","value 3.5"\n"value 4.1","value 4.2","value 4.3","value 4.4","value 4.5"\n"value 5.1","value 5.2","value 5.3","value 5.4","value 5.5"\n', ',', True, id='simple quoted fields'),
    pytest.param('col1,col2,col3,col4,col5\nval1.1,val1.2,val1.3,val1.4,val1.5\nval2.1,val2.2,val2.3,val2.4,val2.5\nval3.1,val3.2,val3.3,val3.4,val3.5\nval4.1,val4.2,val4.3,val4.4,val4.5\nval5.1,val5.2,val5.3,val5.4,val5.5\n', ',', True, id='debug mode'),
    pytest.param('col1,col2,col3,col4\n', ',', False, id='single row'),
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("text, field_sep, expected", INLINE_CASES)
def test_inferh_reference_inline_cases(text: str, field_sep: str, expected: bool) -> None:
    assert has_header(text.splitlines(), field_sep) is expected


@pytest.mark.parametrize(
    "name, field_sep, expected",
    [
        ("seps_test_base", " ", False),
        ("ls_sq", " ", False),
        ("company_funding_data.csv", ",", True),
        ("addresses_reordered", ",", True),
    ],
)
def test_inferh_reference_file_cases(name: str, field_sep: str, expected: bool) -> None:
    lines = (DATA / name).read_text(encoding="utf-8", errors="replace").splitlines()
    assert has_header(lines, field_sep) is expected


def test_inferh_fewer_than_two_rows_has_no_score() -> None:
    assert header_score([], ",") is None
    assert header_score(["col1,col2,col3,col4"], ",") is None
    assert has_header(["col1,col2,col3,col4"], ",") is False


def test_split_row_honours_quotes() -> None:
    assert split_row('"a, b",c', ",") == ["a, b", "c"]
    assert split_row("a  b", " ") == ["a", "b"]


def test_inferh_cli_exit_codes(runner: CliRunner, tmp_path: Path) -> None:
    yes = runner.invoke(cli, [".", "inferh", str(DATA / "company_funding_data.csv")])
    assert yes.exit_code == 0
    p = tmp_path / "nums.csv"
    p.write_text("1,2,3\n4,5,6\n7,8,9\n", encoding="utf-8")
    no = runner.invoke(cli, [".", "inferh", str(p), "-s", ","])
    assert no.exit_code == 1


def test_inferh_cli_stdin_with_separator(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "inferh", "-s", "|"],
                           input="Name|Phone\nJohn|123-456\nJane|234-567\n")
    assert result.exit_code == 0


def test_inferh_cli_single_row_and_empty_exit_1(runner: CliRunner) -> None:
    assert runner.invoke(cli, [".", "inferh"], input="col1,col2\n").exit_code == 1
    assert runner.invoke(cli, [".", "inferh"], input="").exit_code == 1


def test_inferh_cli_verbose_prints_score(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "inferh", "-s", ",", "-v"], input="a,b\n1,2\n")
    assert result.output.startswith("header score: ")
