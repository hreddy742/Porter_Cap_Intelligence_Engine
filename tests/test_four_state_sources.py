"""Source-shaped parsing and end-to-end verification for the four review states."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.connectors.colorado_connector import ColoradoOpenDataConnector
from porter_verify.connectors.connecticut import parse_ct_record
from porter_verify.connectors.connecticut_connector import ConnecticutOpenDataConnector
from porter_verify.connectors.ohio import parse_oh_record
from porter_verify.connectors.ohio_connector import OhioOpenDataConnector
from porter_verify.connectors.ohio_ingest import ingest_oh_file
from porter_verify.connectors.oregon import pivot_or_rows
from porter_verify.connectors.oregon_connector import OregonOpenDataConnector
from porter_verify.db.base import Base
from porter_verify.db.enums import VerificationStatus
from porter_verify.db.models import (
    BusinessRegistration,
    CoBusinessEntity,
    CtBusinessEntity,
    OhBusinessEntity,
    OrBusinessEntity,
)
from porter_verify.services.evidence import EvidenceStore
from porter_verify.services.normalization import normalize_name
from porter_verify.workers.verify_flow import run_verification


def test_connecticut_current_schema_and_sentinel_date() -> None:
    record = parse_ct_record(
        {
            "accountnumber": "1234567",
            "name": "Review Company LLC",
            "status": "Active",
            "business_type": "LLC",
            "date_registration": "0001-01-01T00:00:00.000",
            "billingstreet": "1 Main St",
            "billing_unit": "Suite 2",
            "billingcity": "Hartford",
            "billingstate": "CT",
            "billingpostalcode": "06103",
            "mailing_address": "PO Box 9 Hartford CT 06101",
            "state_or_territory_formation": "Connecticut",
            "country_formation": "United States",
        }
    )
    assert record.formation_date is None
    assert record.principal_address == "1 Main St Suite 2 Hartford CT 06103"
    assert record.mailing_address == "PO Box 9 Hartford CT 06101"
    assert record.jurisdiction == "Connecticut United States"


def test_oregon_long_rows_preserve_agent_representatives_and_raw() -> None:
    rows = [
        {
            "registry_number": "123456",
            "business_name": "Review Company LLC",
            "associated_name_type": "PRINCIPAL PLACE OF BUSINESS",
            "entity_type": "DOMESTIC LIMITED LIABILITY COMPANY",
            "registry_date": "2024-01-02",
            "address": "1 Main St",
            "city": "Salem",
            "state": "OR",
            "zip": "97301",
            "business_details": {"url": "https://example.test/123456"},
        },
        {
            "registry_number": "123456",
            "associated_name_type": "REGISTERED AGENT",
            "first_name": "Jane",
            "last_name": "Agent",
            "address": "2 State St",
            "city": "Salem",
            "state": "OR",
            "zip": "97301",
        },
        {
            "registry_number": "123456",
            "associated_name_type": "AUTHORIZED REPRESENTATIVE",
            "first_name": "John",
            "last_name": "Owner",
        },
    ]
    record = pivot_or_rows(rows)
    assert record is not None
    assert record.agent_name == "Jane Agent"
    assert record.principal_address == "1 Main St Salem OR 97301"
    assert record.officers[0]["name"] == "John Owner"
    assert record.source_record_url == "https://example.test/123456"
    assert record.raw == {"rows": rows}


def test_ohio_alias_parser_and_zip_ingest(db_session, tmp_path: Path) -> None:
    row = {
        "Charter Number": "OH-100",
        "Business Name": "Review Company LLC",
        "Entity Status": "Active",
        "Business Type": "Domestic Limited Liability Company",
        "Filing Date": "01/02/2024",
        "Business Address": "1 Main St Columbus OH 43215",
        "Statutory Agent": "Jane Agent",
    }
    record = parse_oh_record(row)
    assert record.entity_id == "OH-100"
    assert record.formation_date is not None and record.formation_date.year == 2024

    csv_path = tmp_path / "businesses.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    zip_path = tmp_path / "ohio.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(csv_path, csv_path.name)

    assert ingest_oh_file(db_session, zip_path) == 1
    assert db_session.get(OhBusinessEntity, "OH-100") is not None


@pytest.mark.parametrize(
    ("state", "model", "connector_type"),
    [
        ("CO", CoBusinessEntity, ColoradoOpenDataConnector),
        ("CT", CtBusinessEntity, ConnecticutOpenDataConnector),
        ("OR", OrBusinessEntity, OregonOpenDataConnector),
        ("OH", OhBusinessEntity, OhioOpenDataConnector),
    ],
)
def test_four_state_end_to_end(
    tmp_path: Path,
    state: str,
    model: type,
    connector_type: type,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / f'{state}.sqlite3'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    entity_id = f"{state}-100"
    with factory() as session:
        session.add(
            model(
                entity_id=entity_id,
                entity_name="Review Company LLC",
                normalized_name=normalize_name("Review Company LLC"),
                status_raw="Good Standing" if state == "CO" else "Active",
                entity_type="LLC",
                principal_address="1 Main St",
                mailing_address="PO Box 2",
                jurisdiction=state,
                source_record_url=f"https://example.test/{entity_id}",
                agent_name="Jane Agent",
                agent_address="2 State St",
                officers=[],
                raw={"source": state},
            )
        )
        session.commit()

    registry = ConnectorRegistry()
    registry.register(connector_type(factory))
    with factory() as session:
        outcome = run_verification(
            session,
            registry=registry,
            evidence_store=EvidenceStore(tmp_path / f"evidence-{state}"),
            name="Review Company LLC",
            state=state,
        )
    assert outcome.verification_status is VerificationStatus.VERIFIED
    with factory() as session:
        registration = session.scalar(select(BusinessRegistration))
        assert registration is not None
        assert registration.mailing_address == "PO Box 2"
        assert registration.jurisdiction == state
        assert registration.source_record_url == f"https://example.test/{entity_id}"
    engine.dispose()
