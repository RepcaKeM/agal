"""Tests for Polish Tech Job Hub MCP server and normalization logic."""

import pytest
import time
from servers.job_hub.job_hub_mcp import (
    _normalize_nfj_offer,
    _normalize_jjit_offer,
    _NFJ_CACHE,
    search_nofluffjobs,
    search_polish_jobs,
)


def test_normalize_nfj_offer_with_b2b_salary():
    post = {
        "id": "python-dev-123",
        "title": "Senior Python Developer",
        "name": "Acme Corp",
        "url": "python-dev-123",
        "location": {
            "places": [{"city": "Warszawa"}],
            "fullyRemote": True,
            "hybridDesc": "",
        },
        "salary": {
            "from": 120.0,
            "to": 150.0,
            "type": "b2b",
            "currency": "PLN",
            "period": "Hour",
        },
        "seniority": ["Senior"],
        "tiles": {
            "values": [
                {"value": "Python", "type": "requirement"},
                {"value": "FastAPI", "type": "requirement"},
            ]
        },
    }

    normalized = _normalize_nfj_offer(post)
    assert normalized["source"] == "nofluffjobs"
    assert normalized["title"] == "Senior Python Developer"
    assert normalized["company"] == "Acme Corp"
    assert normalized["url"] == "https://nofluffjobs.com/job/python-dev-123"
    assert normalized["location"] == "Remote"
    assert normalized["work_mode"] == "remote"
    assert normalized["seniority"] == "Senior"
    assert normalized["contract_types"] == ["b2b"]
    assert normalized["salary_min"] == 120.0
    assert normalized["salary_max"] == 150.0
    assert normalized["salary_currency"] == "PLN"
    assert normalized["salary_display"] == "B2B: 120–150 PLN/h"
    assert "Python" in normalized["skills"]
    assert "FastAPI" in normalized["skills"]


def test_normalize_nfj_offer_no_salary():
    post = {
        "id": "junior-qa",
        "title": "Junior QA",
        "name": "TestLab",
        "url": "junior-qa",
        "location": {
            "places": [{"city": "Kraków"}],
            "fullyRemote": False,
            "hybridDesc": "2 dni w biurze",
        },
        "salary": None,
        "seniority": ["Junior"],
        "tiles": {"values": []},
    }

    normalized = _normalize_nfj_offer(post)
    assert normalized["salary_display"] == "Brak podanych widełek"
    assert normalized["salary_min"] is None
    assert normalized["salary_max"] is None
    assert normalized["work_mode"] == "hybrid"
    assert normalized["location"] == "Kraków"


def test_normalize_jjit_offer_with_schema_org():
    raw_ld = {
        "title": "Lead Python Engineer",
        "hiringOrganization": {"name": "Globex IT"},
        "baseSalary": {
            "currency": "PLN",
            "value": {
                "unitText": "MONTH",
                "minValue": 25000,
                "maxValue": 32000,
            },
        },
        "employmentType": "CONTRACTOR",
        "jobLocation": {
            "address": {
                "addressLocality": "Wrocław",
            }
        },
        "description": "Fully remote role with Python and AWS.",
    }
    url = "https://justjoin.it/job-offer/globex-lead-python-wroclaw"

    normalized = _normalize_jjit_offer(raw_ld, url)
    assert normalized["source"] == "justjoinit"
    assert normalized["id"] == "globex-lead-python-wroclaw"
    assert normalized["title"] == "Lead Python Engineer"
    assert normalized["company"] == "Globex IT"
    assert normalized["salary_min"] == 25000.0
    assert normalized["salary_max"] == 32000.0
    assert normalized["salary_display"] == "25000–32000 PLN/m-c"
    assert "b2b" in normalized["contract_types"]
    assert normalized["work_mode"] == "remote"


def test_search_nofluffjobs_filtering(monkeypatch):
    import asyncio
    async def _run():
        sample_postings = [
            {
                "id": "1",
                "title": "Senior Python Backend Developer",
                "name": "Alpha",
                "category": "backend",
                "location": {"places": [{"city": "Warszawa"}], "fullyRemote": True},
                "salary": {"from": 20000, "to": 25000, "type": "b2b", "currency": "PLN", "period": "Month"},
                "seniority": ["Senior"],
                "tiles": {"values": [{"value": "Python"}, {"value": "Django"}]},
            },
            {
                "id": "2",
                "title": "Java Developer",
                "name": "Beta",
                "category": "backend",
                "location": {"places": [{"city": "Kraków"}], "fullyRemote": False},
                "salary": {"from": 15000, "to": 18000, "type": "uop", "currency": "PLN", "period": "Month"},
                "seniority": ["Mid"],
                "tiles": {"values": [{"value": "Java"}, {"value": "Spring"}]},
            },
        ]

        # Populate cache directly to avoid external network calls
        _NFJ_CACHE["data"] = sample_postings
        _NFJ_CACHE["timestamp"] = time.time()

        # Search by keyword
        results_py = await search_nofluffjobs(keyword="python", limit=10)
        assert len(results_py) == 1
        assert results_py[0]["company"] == "Alpha"

        # Search by seniority
        results_mid = await search_nofluffjobs(keyword="java", seniority="mid", limit=10)
        assert len(results_mid) == 1
        assert results_mid[0]["company"] == "Beta"

        # Search with remote filter
        results_rem = await search_nofluffjobs(keyword="java", location="remote", limit=10)
        assert len(results_rem) == 0

    asyncio.run(_run())


def test_search_polish_jobs_deduplication(monkeypatch):
    import asyncio
    async def _run():
        # Mock search_nofluffjobs and search_justjoin_it
        async def mock_nfj(**kwargs):
            return [
                {
                    "source": "nofluffjobs",
                    "id": "nfj-1",
                    "title": "Senior Python Architect",
                    "company": "EPAM Systems",
                    "url": "https://nofluffjobs.com/job/1",
                    "salary_display": "B2B: 30k PLN",
                }
            ]

        async def mock_jjit(**kwargs):
            return [
                {
                    "source": "justjoinit",
                    "id": "jjit-1",
                    "title": "Senior Python Architect",
                    "company": "EPAM Systems",
                    "url": "https://justjoin.it/job-offer/epam-arch",
                    "salary_display": "B2B: 30k PLN",
                },
                {
                    "source": "justjoinit",
                    "id": "jjit-2",
                    "title": "DevOps Engineer",
                    "company": "Amazon",
                    "url": "https://justjoin.it/job-offer/amazon-devops",
                    "salary_display": "UoP: 25k PLN",
                },
            ]

        monkeypatch.setattr("servers.job_hub.job_hub_mcp.search_nofluffjobs", mock_nfj)
        monkeypatch.setattr("servers.job_hub.job_hub_mcp.search_justjoin_it", mock_jjit)

        combined = await search_polish_jobs(keyword="python", limit=10, source="all")
        # Duplicate EPAM Senior Python Architect should be deduplicated
        assert len(combined) == 2
        companies = [c["company"] for c in combined]
        assert "EPAM Systems" in companies
        assert "Amazon" in companies

    asyncio.run(_run())
