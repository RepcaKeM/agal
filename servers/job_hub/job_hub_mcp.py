"""
Polish Tech Job Hub - MCP Server for JustJoinIT and NoFluffJobs.

Provides low-latency, zero-cost search across Polish IT job boards
with standardized JobOffer schema and in-memory caching.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Optional
from bs4 import BeautifulSoup

# Setup logging to stderr so stdio JSON-RPC isn't corrupted
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("polish-job-hub")

# Compatibility layer for MCP 2.x (MCPServer) and MCP 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer
    mcp_app = MCPServer("Polish Tech Job Hub")
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        mcp_app = FastMCP("Polish Tech Job Hub")
    except ImportError as e:
        logger.error("Failed to import MCP server library: %s", e)
        raise

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# In-memory cache for NoFluffJobs (TTL: 20 minutes)
_NFJ_CACHE: dict[str, Any] = {
    "timestamp": 0.0,
    "data": [],
}
_NFJ_LOCK = asyncio.Lock()
NFJ_CACHE_TTL_SECONDS = 1200.0  # 20 minutes


def _http_get_sync(url: str, timeout: float = 12.0) -> str:
    """Synchronous HTTP GET with browser-like headers."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


async def http_get(url: str, timeout: float = 12.0) -> str:
    """Async wrapper for non-blocking HTTP GET."""
    return await asyncio.to_thread(_http_get_sync, url, timeout)


# ==============================================================================
# NoFluffJobs Core
# ==============================================================================

async def _get_nfj_postings() -> list[dict]:
    """Fetch all postings from NoFluffJobs with in-memory caching."""
    global _NFJ_CACHE
    now = time.time()
    if _NFJ_CACHE["data"] and (now - _NFJ_CACHE["timestamp"]) < NFJ_CACHE_TTL_SECONDS:
        return _NFJ_CACHE["data"]

    async with _NFJ_LOCK:
        # Check again in case another coroutine fetched while waiting for lock
        now = time.time()
        if _NFJ_CACHE["data"] and (now - _NFJ_CACHE["timestamp"]) < NFJ_CACHE_TTL_SECONDS:
            return _NFJ_CACHE["data"]

        logger.info("Fetching fresh postings from NoFluffJobs API...")
        try:
            raw_json = await http_get("https://nofluffjobs.com/api/posting", timeout=15.0)
            data = json.loads(raw_json)
            postings = data.get("postings", [])
            _NFJ_CACHE["data"] = postings
            _NFJ_CACHE["timestamp"] = now
            logger.info("Cached %d NoFluffJobs postings.", len(postings))
            return postings
        except Exception as e:
            logger.error("Failed to fetch NoFluffJobs postings: %s", e)
            if _NFJ_CACHE["data"]:
                logger.warning("Serving stale NoFluffJobs cache as fallback.")
                return _NFJ_CACHE["data"]
            return []


def _normalize_nfj_offer(post: dict) -> dict:
    """Normalize a NoFluffJobs posting into the standard JobOffer schema."""
    salary_raw = post.get("salary", {}) or {}
    s_from = salary_raw.get("from")
    s_to = salary_raw.get("to")
    s_currency = salary_raw.get("currency")
    s_type = salary_raw.get("type", "").lower()
    s_period = salary_raw.get("period", "").lower()

    if s_from is not None or s_to is not None:
        type_str = s_type.upper() if s_type else "B2B/UoP"
        period_str = "h" if "hour" in s_period else "m-c"
        if s_from and s_to:
            salary_display = f"{type_str}: {int(s_from)}–{int(s_to)} {s_currency}/{period_str}"
        elif s_to:
            salary_display = f"{type_str}: do {int(s_to)} {s_currency}/{period_str}"
        else:
            salary_display = f"{type_str}: od {int(s_from)} {s_currency}/{period_str}"
    else:
        salary_display = "Brak podanych widełek"

    loc_obj = post.get("location", {}) or {}
    places = loc_obj.get("places", []) or []
    city = places[0].get("city", "Remote") if places else "Remote"
    is_remote = bool(loc_obj.get("fullyRemote")) or any(p.get("city") == "Remote" for p in places)

    skills = []
    tiles = post.get("tiles", {}).get("values", [])
    for t in tiles:
        val = t.get("value")
        if val and val not in skills:
            skills.append(val)

    seniority_list = post.get("seniority", [])
    seniority = ", ".join(seniority_list) if seniority_list else "N/A"

    return {
        "source": "nofluffjobs",
        "id": str(post.get("id", "")),
        "title": post.get("title", ""),
        "company": post.get("name", ""),
        "url": f"https://nofluffjobs.com/job/{post.get('url', '')}",
        "location": "Remote" if is_remote else city,
        "work_mode": "remote" if is_remote else ("hybrid" if loc_obj.get("hybridDesc") else "office"),
        "seniority": seniority,
        "contract_types": [s_type] if s_type else [],
        "salary_min": float(s_from) if s_from is not None else None,
        "salary_max": float(s_to) if s_to is not None else None,
        "salary_currency": s_currency,
        "salary_period": s_period,
        "salary_display": salary_display,
        "skills": skills[:8],
    }


# ==============================================================================
# JustJoinIT Core
# ==============================================================================

async def _fetch_jjit_offer_details(offer_url: str) -> Optional[dict]:
    """Fetch details of a single JustJoinIT offer and parse JobPosting JSON-LD."""
    try:
        html = await http_get(offer_url, timeout=8.0)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    return data
            except Exception:
                continue
    except Exception as e:
        logger.debug("Failed to fetch JJIT offer %s: %s", offer_url, e)
    return None


def _normalize_jjit_offer(raw: dict, offer_url: str) -> dict:
    """Normalize a JustJoinIT JobPosting JSON-LD into the standard JobOffer schema."""
    title = raw.get("title", "")
    company = raw.get("hiringOrganization", {}).get("name", "")
    base_salary = raw.get("baseSalary", {}) or {}
    val = base_salary.get("value", {}) if isinstance(base_salary, dict) else {}

    s_min = val.get("minValue") if isinstance(val, dict) else None
    s_max = val.get("maxValue") if isinstance(val, dict) else None
    s_curr = base_salary.get("currency") if isinstance(base_salary, dict) else None
    s_unit = val.get("unitText", "").lower() if isinstance(val, dict) else ""

    if s_min is not None or s_max is not None:
        period_str = "h" if "hour" in s_unit else "m-c"
        if s_min and s_max:
            salary_display = f"{int(s_min)}–{int(s_max)} {s_curr or 'PLN'}/{period_str}"
        elif s_max:
            salary_display = f"do {int(s_max)} {s_curr or 'PLN'}/{period_str}"
        else:
            salary_display = f"od {int(s_min)} {s_curr or 'PLN'}/{period_str}"
    else:
        salary_display = "Brak podanych widełek"

    emp_type = raw.get("employmentType", "")
    contract_types = []
    if "CONTRACTOR" in emp_type:
        contract_types.append("b2b")
    if "FULL_TIME" in emp_type or "EMPLOYEE" in emp_type:
        contract_types.append("uop")

    loc = raw.get("jobLocation", {})
    addr = loc.get("address", {}) if isinstance(loc, dict) else {}
    city = addr.get("addressLocality", "") if isinstance(addr, dict) else ""

    desc = raw.get("description", "")
    is_remote = "remote" in desc.lower() or "zdaln" in desc.lower()
    work_mode = "remote" if is_remote else ("hybrid" if "hybrid" in desc.lower() else "office")

    # Extract slug for ID
    slug_match = re.search(r"/job-offer/([a-zA-Z0-9_\-]+)", offer_url)
    offer_id = slug_match.group(1) if slug_match else offer_url

    return {
        "source": "justjoinit",
        "id": offer_id,
        "title": title,
        "company": company,
        "url": offer_url,
        "location": "Remote" if is_remote and not city else (city or "Remote"),
        "work_mode": work_mode,
        "seniority": "Senior" if "senior" in title.lower() else ("Junior" if "junior" in title.lower() else "Mid"),
        "contract_types": contract_types,
        "salary_min": float(s_min) if s_min is not None else None,
        "salary_max": float(s_max) if s_max is not None else None,
        "salary_currency": s_curr,
        "salary_period": "hour" if "hour" in s_unit else "month",
        "salary_display": salary_display,
        "skills": [],
    }


# ==============================================================================
# FastMCP Tools
# ==============================================================================

@mcp_app.tool()
async def search_nofluffjobs(
    keyword: str = "python",
    location: str = "",
    limit: int = 10,
    seniority: str = "",
) -> list[dict]:
    """Wyszukuje oferty pracy na No Fluff Jobs po słowie kluczowym, lokalizacji i poziomie doświadczenia.
    
    Args:
        keyword: Słowo kluczowe technologii lub roli (np. 'python', 'react', 'devops')
        location: Filtr lokalizacji ('remote', 'warszawa', 'krakow' itp. - pusty oznacza dowolną)
        limit: Maksymalna liczba ofert do zwrócenia (domyślnie 10)
        seniority: Filtr poziomu ('trainee', 'junior', 'mid', 'senior', 'expert')
    """
    postings = await _get_nfj_postings()
    if not postings:
        return []

    kw = keyword.lower().strip()
    loc = location.lower().strip()
    sen = seniority.lower().strip()

    matches = []
    for post in postings:
        title = post.get("title", "").lower()
        category = post.get("category", "").lower()

        # Check tiles skills
        skills = [t.get("value", "").lower() for t in post.get("tiles", {}).get("values", [])]
        
        # Match keyword
        if kw and not (kw in title or kw in category or any(kw in s for s in skills)):
            continue

        # Match location
        if loc:
            loc_obj = post.get("location", {}) or {}
            places = loc_obj.get("places", []) or []
            is_post_remote = bool(loc_obj.get("fullyRemote")) or any(p.get("city") == "Remote" for p in places)
            if loc == "remote":
                if not is_post_remote:
                    continue
            else:
                cities = [p.get("city", "").lower() for p in places]
                if not any(loc in c for c in cities) and not is_post_remote:
                    continue

        # Match seniority
        if sen:
            post_sen = [s.lower() for s in post.get("seniority", [])]
            if not any(sen in s for s in post_sen):
                continue

        matches.append(_normalize_nfj_offer(post))
        if len(matches) >= limit:
            break

    return matches


@mcp_app.tool()
async def search_justjoin_it(
    keyword: str = "python",
    location: str = "",
    limit: int = 10,
) -> list[dict]:
    """Wyszukuje oferty pracy na Just Join IT po technologii lub tytule.
    
    Args:
        keyword: Słowo kluczowe technologii lub roli (np. 'python', 'javascript', 'ai')
        location: Filtr lokalizacji ('remote' lub nazwa miasta)
        limit: Maksymalna liczba ofert do zwrócenia (domyślnie 10)
    """
    kw_slug = urllib.parse.quote(keyword.lower().strip())
    list_url = f"https://justjoin.it/job-offers/all-locations/{kw_slug}"

    try:
        html = await http_get(list_url, timeout=10.0)
    except Exception as e:
        logger.error("Failed to load JJIT listing page: %s", e)
        return []

    soup = BeautifulSoup(html, "html.parser")
    offer_urls: list[str] = []

    # 1. Parse JSON-LD CollectionPage
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, dict) and data.get("@type") == "CollectionPage":
                parts = data.get("hasPart", [])
                for p in parts:
                    u = p.get("url")
                    if u and u not in offer_urls:
                        offer_urls.append(u)
        except Exception:
            continue

    # 2. Fallback to regex if JSON-LD missing
    if not offer_urls:
        slugs = set(re.findall(r"/job-offer/([a-zA-Z0-9_\-]+)", html))
        offer_urls = [f"https://justjoin.it/job-offer/{s}" for s in slugs]

    if not offer_urls:
        return []

    # Filter details for candidates (up to limit * 2 to account for location filters)
    candidates = offer_urls[: min(limit * 2, 20)]
    results: list[dict] = []
    loc_filter = location.lower().strip()

    for url in candidates:
        detail = await _fetch_jjit_offer_details(url)
        if not detail:
            continue

        normalized = _normalize_jjit_offer(detail, url)

        # Apply location filter if requested
        if loc_filter:
            if loc_filter == "remote" and normalized["work_mode"] != "remote":
                continue
            elif loc_filter != "remote" and loc_filter not in normalized["location"].lower() and normalized["work_mode"] != "remote":
                continue

        results.append(normalized)
        if len(results) >= limit:
            break

        # Polite delay to prevent throttling
        await asyncio.sleep(0.15)

    return results


@mcp_app.tool()
async def search_polish_jobs(
    keyword: str = "python",
    location: str = "",
    limit: int = 10,
    source: str = "all",
) -> list[dict]:
    """Wyszukuje oferty równocześnie na NoFluffJobs i JustJoinIT z automatyczną deduplikacją.
    
    Args:
        keyword: Słowo kluczowe (np. 'python', 'devops')
        location: Lokalizacja ('remote', 'warszawa', itp.)
        limit: Łączny limit zwróconych unikalnych ofert (domyślnie 10)
        source: Wybór źródła: 'all', 'nofluffjobs', 'justjoinit'
    """
    src = source.lower().strip()
    half_limit = max(1, limit // 2)

    tasks = []
    if src in ("all", "nofluffjobs", "nfj"):
        tasks.append(search_nofluffjobs(keyword=keyword, location=location, limit=half_limit if src == "all" else limit))
    if src in ("all", "justjoinit", "jjit"):
        tasks.append(search_justjoin_it(keyword=keyword, location=location, limit=half_limit if src == "all" else limit))

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    all_offers: list[dict] = []
    for res in gathered:
        if isinstance(res, list):
            all_offers.extend(res)
        elif isinstance(res, Exception):
            logger.error("Source error: %s", res)

    # Cross-portal deduplication: company + title similarity
    seen_signatures = set()
    deduplicated = []

    for offer in all_offers:
        comp_norm = re.sub(r"[^a-zA-Z0-9]", "", offer.get("company", "").lower())
        title_norm = re.sub(r"[^a-zA-Z0-9]", "", offer.get("title", "").lower()[:30])
        sig = f"{comp_norm}:{title_norm}"

        if sig in seen_signatures and comp_norm:
            continue
        seen_signatures.add(sig)
        deduplicated.append(offer)
        if len(deduplicated) >= limit:
            break

    return deduplicated


if __name__ == "__main__":
    # Run FastMCP stdio server
    mcp_app.run()
