"""
Async GBIF Species API client with in-memory 24h cache.

Flow for a given species name:
  1. GET /species/match?name=<species>   → usageKey, taxonomy tree, matchType
  2. GET /species/<usageKey>             → authorship, maybe vernacularName
  3. GET /species/<usageKey>/vernacularNames  (only if step 2 returned no name)
     → prefer Spanish, then English, then first available

source_status values:
  "ok"           — matchType EXACT
  "fuzzy_match"  — matchType FUZZY | HIGHERRANK | AGGREGATE (usable, not exact)
  "not_found"    — matchType NONE or no usageKey
  "unavailable"  — network / HTTP error
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_GBIF_BASE = "https://api.gbif.org/v1"
_TTL = timedelta(hours=24)
_TIMEOUT = 10.0  # seconds per request


@dataclass
class GbifTaxonomyData:
    kingdom: Optional[str] = None
    phylum: Optional[str] = None
    taxon_class: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    specific_epithet: Optional[str] = None
    scientific_name: Optional[str] = None
    scientific_name_authorship: Optional[str] = None
    taxon_rank: Optional[str] = None
    vernacular_name: Optional[str] = None
    gbif_usage_key: Optional[int] = None
    gbif_confidence: Optional[int] = None
    gbif_match_type: Optional[str] = None


@dataclass
class _CacheEntry:
    taxonomy: Optional[GbifTaxonomyData]
    source_status: str
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Module-level in-memory store: species_key → _CacheEntry
_cache: dict[str, _CacheEntry] = {}


def _cache_key(species: str) -> str:
    return species.strip().lower()


def _is_fresh(entry: _CacheEntry) -> bool:
    return (datetime.now(timezone.utc) - entry.cached_at) < _TTL


def _pick_vernacular(results: list[dict]) -> Optional[str]:
    """Prefer Spanish, then English, then first available vernacular name."""
    for lang_prefix in ("spa", "es"):
        for r in results:
            if r.get("language", "").lower().startswith(lang_prefix) and r.get("vernacularName"):
                return r["vernacularName"]
    for lang_prefix in ("eng", "en"):
        for r in results:
            if r.get("language", "").lower().startswith(lang_prefix) and r.get("vernacularName"):
                return r["vernacularName"]
    for r in results:
        if r.get("vernacularName"):
            return r["vernacularName"]
    return None


def _specific_epithet(species: str) -> Optional[str]:
    parts = species.strip().split()
    return parts[1] if len(parts) >= 2 else None


async def fetch_taxonomy(species: str) -> tuple[Optional[GbifTaxonomyData], str]:
    """
    Return (GbifTaxonomyData | None, source_status).
    Results are cached in memory for 24 h.
    """
    key = _cache_key(species)

    if key in _cache and _is_fresh(_cache[key]):
        logger.debug("GBIF cache hit for %r", species)
        entry = _cache[key]
        return entry.taxonomy, entry.source_status

    logger.debug("GBIF fetch for %r", species)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # ── Call 1: species/match ─────────────────────────────────────────
            r1 = await client.get(
                f"{_GBIF_BASE}/species/match",
                params={"name": species, "verbose": "false"},
            )
            r1.raise_for_status()
            match = r1.json()

        match_type: str = match.get("matchType", "NONE")
        usage_key: Optional[int] = match.get("usageKey")

        if match_type == "NONE" or not usage_key:
            _store(key, None, "not_found")
            return None, "not_found"

        if match_type == "EXACT":
            source_status = "ok"
        else:
            # FUZZY, HIGHERRANK, AGGREGATE — usable but imprecise
            source_status = "fuzzy_match"

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # ── Call 2: species/{usageKey} ────────────────────────────────────
            r2 = await client.get(f"{_GBIF_BASE}/species/{usage_key}")
            r2.raise_for_status()
            detail = r2.json()

            vernacular: Optional[str] = detail.get("vernacularName") or None

            # ── Call 3: vernacularNames (only if not found in detail) ──────────
            if not vernacular:
                try:
                    r3 = await client.get(
                        f"{_GBIF_BASE}/species/{usage_key}/vernacularNames",
                        params={"limit": 20},
                    )
                    r3.raise_for_status()
                    vernacular = _pick_vernacular(r3.json().get("results", []))
                except httpx.HTTPError:
                    # vernacularNames is optional — don't fail the whole request
                    logger.debug("Could not fetch vernacularNames for usageKey %s", usage_key)

        taxonomy = GbifTaxonomyData(
            kingdom=match.get("kingdom"),
            phylum=match.get("phylum"),
            taxon_class=match.get("class"),
            order=match.get("order"),
            family=match.get("family"),
            genus=match.get("genus"),
            specific_epithet=_specific_epithet(species),
            scientific_name=detail.get("scientificName") or match.get("scientificName"),
            scientific_name_authorship=detail.get("authorship") or None,
            taxon_rank=match.get("rank"),
            vernacular_name=vernacular,
            gbif_usage_key=usage_key,
            gbif_confidence=match.get("confidence"),
            gbif_match_type=match_type,
        )

        _store(key, taxonomy, source_status)
        logger.info("GBIF %r → %s (key=%s)", species, source_status, usage_key)
        return taxonomy, source_status

    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("GBIF network error for %r: %s", species, exc)
        _store(key, None, "unavailable")
        return None, "unavailable"

    except httpx.HTTPStatusError as exc:
        logger.warning("GBIF HTTP %s for %r", exc.response.status_code, species)
        _store(key, None, "unavailable")
        return None, "unavailable"


def _store(key: str, taxonomy: Optional[GbifTaxonomyData], status: str) -> None:
    _cache[key] = _CacheEntry(taxonomy=taxonomy, source_status=status)


def clear_cache() -> None:
    """Evict all cached entries (useful in tests)."""
    _cache.clear()
