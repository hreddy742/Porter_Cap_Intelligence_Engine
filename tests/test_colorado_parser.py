"""Tests for the Colorado record parser (Feature 1).

Uses rows shaped exactly like the live data.colorado.gov dataset.
"""

from __future__ import annotations

from datetime import date

from porter_verify.connectors.colorado import parse_co_date, parse_record

# A row with an organization agent, mirroring the real schema.
ROW_ORG_AGENT = {
    "entityid": "20251665680",
    "entityname": "KYLDERON MIST VALLEY LLC",
    "entitystatus": "Good Standing",
    "entitytype": "DLLC",
    "entityformdate": "2025-06-16T00:00:00.000",
    "principaladdress1": "123 Main St",
    "principaladdress2": "",
    "principalcity": "Delta",
    "principalstate": "CO",
    "principalzipcode": "81416",
    "agentfirstname": "",
    "agentmiddlename": "",
    "agentlastname": "",
    "agentsuffix": "",
    "agentorganizationname": "Registered Agents Inc",
    "agentprincipaladdress1": "1 Plaza",
    "agentprincipalcity": "Denver",
    "agentprincipalstate": "CO",
    "agentprincipalzipcode": "80202",
}

# A row with a person agent and a delinquent status.
ROW_PERSON_AGENT = {
    "entityid": "19871342214",
    "entityname": "SOUTHWEST CONTRACTING, LLC",
    "entitystatus": "Delinquent",
    "entitytype": "DLLC",
    "entityformdate": "1978-02-28T00:00:00.000",
    "principalcity": "Cortez",
    "principalstate": "CO",
    "agentfirstname": "Maria",
    "agentmiddlename": "",
    "agentlastname": "Franchini",
    "agentsuffix": "",
    "agentorganizationname": "",
}


def test_parse_date_takes_date_prefix() -> None:
    assert parse_co_date("2025-06-16T00:00:00.000") == date(2025, 6, 16)


def test_parse_date_handles_blank_and_bad() -> None:
    assert parse_co_date("") is None
    assert parse_co_date(None) is None
    assert parse_co_date("not-a-date") is None


def test_parse_record_organization_agent() -> None:
    rec = parse_record(ROW_ORG_AGENT)
    assert rec.entity_id == "20251665680"
    assert rec.legal_name == "KYLDERON MIST VALLEY LLC"
    assert rec.status_raw == "Good Standing"
    assert rec.entity_type == "DLLC"
    assert rec.formation_date == date(2025, 6, 16)
    assert rec.principal_address == "123 Main St Delta CO 81416"
    assert rec.agent_name == "Registered Agents Inc"  # org wins
    assert rec.agent_address == "1 Plaza Denver CO 80202"
    assert rec.raw["entityid"] == "20251665680"  # raw preserved


def test_parse_record_person_agent() -> None:
    rec = parse_record(ROW_PERSON_AGENT)
    assert rec.agent_name == "Maria Franchini"  # person name assembled
    assert rec.status_raw == "Delinquent"
    assert rec.principal_address == "Cortez CO"  # only the present parts


def test_parse_record_tolerates_missing_fields() -> None:
    rec = parse_record({"entityid": "1", "entityname": "X"})
    assert rec.status_raw is None
    assert rec.formation_date is None
    assert rec.agent_name is None
    assert rec.principal_address is None
