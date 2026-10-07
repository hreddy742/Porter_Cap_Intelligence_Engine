"""Tests for New Jersey targeted UCC public-search parsing."""

from __future__ import annotations

from datetime import date

from porter_verify.connectors.new_jersey_ucc import (
    parse_new_jersey_ucc_results,
    to_public_search_results,
)


def test_parse_new_jersey_ucc_results_from_status_table() -> None:
    html = """
    <table id="ctl00_mainContent_DebtorSearch1_Wizard1_orgResults_orgResultsGridView">
      <tr>
        <th>Select</th><th>Organization</th><th>City</th><th>Filing Number</th>
        <th>Filing Status</th><th>Filing Date</th><th>Filing Date</th><th>Page Count</th>
      </tr>
      <tr>
        <td><input type="checkbox" /></td><td>WALMART INC.</td><td>BENTONVILLE</td>
        <td>58308035</td><td>Active</td><td>03/27/2026</td>
        <td>3/27/2026 12:00:00 AM</td><td>64</td>
      </tr>
    </table>
    """

    rows = parse_new_jersey_ucc_results(html)

    assert len(rows) == 1
    assert rows[0].organization_name == "WALMART INC."
    assert rows[0].filing_number == "58308035"
    assert rows[0].filing_date == date(2026, 3, 27)
    assert rows[0].page_count == 64


def test_to_public_search_results_marks_new_jersey_provenance() -> None:
    row = parse_new_jersey_ucc_results(
        """
        <table id="ctl00_mainContent_DebtorSearch1_Wizard1_orgResults_orgResultsGridView">
          <tr><th></th><th>Organization</th><th>City</th><th>Filing Number</th>
          <th>Filing Status</th><th>Filing Date</th><th>Filing Date</th><th>Page Count</th></tr>
          <tr><td></td><td>WALMART INC.</td><td>BENTONVILLE</td><td>58308035</td>
          <td>Active</td><td>03/27/2026</td><td>3/27/2026 12:00:00 AM</td><td>64</td></tr>
        </table>
        """
    )[0]

    result = to_public_search_results("WALMART", [row])[0]

    assert result.state == "NJ"
    assert result.filing_id == "58308035"
    assert result.debtor_name == "WALMART INC."
    assert result.match_confidence == 90
    assert result.source_url == "https://www.njportal.com/UCC/Search/NonCertifiedSearch.aspx"
