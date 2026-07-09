"""Unit tests for infrastructure/gbif_client.py."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.gbif_client import (
    GbifTaxonomyData,
    _CacheEntry,
    _cache,
    _pick_vernacular,
    _specific_epithet,
    clear_cache,
    fetch_taxonomy,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    r = MagicMock()
    r.json.return_value = json_data
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        r.raise_for_status.side_effect = HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock(status_code=status_code)
        )
    return r


MATCH_EXACT = {
    "matchType": "EXACT",
    "usageKey": 5219404,
    "scientificName": "Panthera onca Linnaeus, 1758",
    "canonicalName": "Panthera onca",
    "rank": "SPECIES",
    "confidence": 99,
    "kingdom": "Animalia",
    "phylum": "Chordata",
    "class": "Mammalia",
    "order": "Carnivora",
    "family": "Felidae",
    "genus": "Panthera",
    "species": "Panthera onca",
}

DETAIL_WITH_VERNACULAR = {
    "scientificName": "Panthera onca Linnaeus, 1758",
    "authorship": "Linnaeus, 1758",
    "vernacularName": "Jaguar",
}

DETAIL_NO_VERNACULAR = {
    "scientificName": "Panthera onca Linnaeus, 1758",
    "authorship": "Linnaeus, 1758",
}

VERNACULAR_NAMES_SPA = {
    "results": [
        {"language": "spa", "vernacularName": "Jaguar"},
        {"language": "eng", "vernacularName": "Jaguar"},
    ]
}

VERNACULAR_NAMES_ENG_ONLY = {
    "results": [
        {"language": "eng", "vernacularName": "Jaguar"},
    ]
}

MATCH_FUZZY = {**MATCH_EXACT, "matchType": "FUZZY", "confidence": 72}
MATCH_HIGHERRANK = {**MATCH_EXACT, "matchType": "HIGHERRANK", "confidence": 60}
MATCH_AGGREGATE = {**MATCH_EXACT, "matchType": "AGGREGATE", "confidence": 55}
MATCH_NONE = {"matchType": "NONE"}


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear the module-level cache before each test."""
    clear_cache()
    yield
    clear_cache()


# ── _pick_vernacular ──────────────────────────────────────────────────────────

class TestPickVernacular:
    def test_prefers_spanish(self):
        results = [
            {"language": "eng", "vernacularName": "Jaguar"},
            {"language": "spa", "vernacularName": "Yaguareté"},
        ]
        assert _pick_vernacular(results) == "Yaguareté"

    def test_falls_back_to_english(self):
        results = [
            {"language": "eng", "vernacularName": "Jaguar"},
            {"language": "deu", "vernacularName": "Jaguar"},
        ]
        assert _pick_vernacular(results) == "Jaguar"

    def test_falls_back_to_first_when_no_spa_eng(self):
        results = [
            {"language": "fra", "vernacularName": "Jaguar"},
        ]
        assert _pick_vernacular(results) == "Jaguar"

    def test_returns_none_for_empty_list(self):
        assert _pick_vernacular([]) is None

    def test_skips_entries_without_name(self):
        results = [{"language": "spa"}, {"language": "eng", "vernacularName": "Jaguar"}]
        assert _pick_vernacular(results) == "Jaguar"


# ── _specific_epithet ─────────────────────────────────────────────────────────

class TestSpecificEpithet:
    def test_binomial(self):
        assert _specific_epithet("Panthera onca") == "onca"

    def test_monomial(self):
        assert _specific_epithet("Panthera") is None

    def test_trinomial(self):
        assert _specific_epithet("Panthera onca onca") == "onca"

    def test_strips_whitespace(self):
        assert _specific_epithet("  Panthera onca  ") == "onca"


# ── fetch_taxonomy ────────────────────────────────────────────────────────────

class TestFetchTaxonomyExact:
    @pytest.mark.asyncio
    async def test_exact_match_returns_ok_status(self):
        responses = [
            _mock_response(MATCH_EXACT),
            _mock_response(DETAIL_WITH_VERNACULAR),
        ]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            taxonomy, status = await fetch_taxonomy("Panthera onca")

        assert status == "ok"
        assert taxonomy is not None
        assert taxonomy.kingdom == "Animalia"
        assert taxonomy.phylum == "Chordata"
        assert taxonomy.taxon_class == "Mammalia"
        assert taxonomy.order == "Carnivora"
        assert taxonomy.family == "Felidae"
        assert taxonomy.genus == "Panthera"
        assert taxonomy.specific_epithet == "onca"
        assert taxonomy.taxon_rank == "SPECIES"
        assert taxonomy.gbif_usage_key == 5219404
        assert taxonomy.gbif_confidence == 99
        assert taxonomy.gbif_match_type == "EXACT"
        assert taxonomy.scientific_name_authorship == "Linnaeus, 1758"
        assert taxonomy.vernacular_name == "Jaguar"

    @pytest.mark.asyncio
    async def test_vernacular_fetched_from_third_call_when_not_in_detail(self):
        responses = [
            _mock_response(MATCH_EXACT),
            _mock_response(DETAIL_NO_VERNACULAR),
            _mock_response(VERNACULAR_NAMES_SPA),
        ]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            taxonomy, status = await fetch_taxonomy("Panthera onca")

        assert status == "ok"
        assert taxonomy.vernacular_name == "Jaguar"
        # Third call was made
        assert instance.get.call_count == 3

    @pytest.mark.asyncio
    async def test_vernacular_prefers_spanish_over_english(self):
        responses = [
            _mock_response(MATCH_EXACT),
            _mock_response(DETAIL_NO_VERNACULAR),
            _mock_response({
                "results": [
                    {"language": "eng", "vernacularName": "Jaguar"},
                    {"language": "spa", "vernacularName": "Yaguareté"},
                ]
            }),
        ]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            taxonomy, _ = await fetch_taxonomy("Panthera onca")

        assert taxonomy.vernacular_name == "Yaguareté"


class TestFetchTaxonomyNonExact:
    @pytest.mark.asyncio
    async def test_fuzzy_match_returns_fuzzy_match_status(self):
        responses = [_mock_response(MATCH_FUZZY), _mock_response(DETAIL_WITH_VERNACULAR)]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            _, status = await fetch_taxonomy("Panthera onca")

        assert status == "fuzzy_match"

    @pytest.mark.asyncio
    async def test_higherrank_returns_fuzzy_match_status(self):
        responses = [_mock_response(MATCH_HIGHERRANK), _mock_response(DETAIL_WITH_VERNACULAR)]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            _, status = await fetch_taxonomy("Panthera onca")

        assert status == "fuzzy_match"

    @pytest.mark.asyncio
    async def test_aggregate_returns_fuzzy_match_status(self):
        responses = [_mock_response(MATCH_AGGREGATE), _mock_response(DETAIL_WITH_VERNACULAR)]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            _, status = await fetch_taxonomy("Panthera onca")

        assert status == "fuzzy_match"


class TestFetchTaxonomyNotFound:
    @pytest.mark.asyncio
    async def test_match_type_none_returns_not_found(self):
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=_mock_response(MATCH_NONE))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            taxonomy, status = await fetch_taxonomy("Xxxxxxxx yyyyyyy")

        assert status == "not_found"
        assert taxonomy is None

    @pytest.mark.asyncio
    async def test_missing_usage_key_returns_not_found(self):
        match_no_key = {**MATCH_EXACT, "matchType": "EXACT"}
        del match_no_key["usageKey"]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=_mock_response(match_no_key))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            taxonomy, status = await fetch_taxonomy("Xxxxxxxx yyyyyyy")

        assert status == "not_found"
        assert taxonomy is None


class TestFetchTaxonomyUnavailable:
    @pytest.mark.asyncio
    async def test_network_error_returns_unavailable(self):
        import httpx as _httpx

        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=_httpx.RequestError("timeout"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            taxonomy, status = await fetch_taxonomy("Panthera onca")

        assert status == "unavailable"
        assert taxonomy is None

    @pytest.mark.asyncio
    async def test_http_status_error_returns_unavailable(self):
        import httpx as _httpx

        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            r = MagicMock()
            r.raise_for_status.side_effect = _httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock(status_code=500)
            )
            instance.get = AsyncMock(return_value=r)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            taxonomy, status = await fetch_taxonomy("Panthera onca")

        assert status == "unavailable"
        assert taxonomy is None


class TestFetchTaxonomyCache:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_http(self):
        """Second call with same species must not hit the network."""
        responses = [_mock_response(MATCH_EXACT), _mock_response(DETAIL_WITH_VERNACULAR)]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            t1, s1 = await fetch_taxonomy("Panthera onca")
            t2, s2 = await fetch_taxonomy("Panthera onca")

        # Only 2 HTTP calls for the first fetch; zero for the second
        assert instance.get.call_count == 2
        assert s1 == s2 == "ok"
        assert t1 is t2

    @pytest.mark.asyncio
    async def test_case_insensitive_cache(self):
        """'panthera onca' and 'Panthera onca' should share the same cache entry."""
        responses = [_mock_response(MATCH_EXACT), _mock_response(DETAIL_WITH_VERNACULAR)]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await fetch_taxonomy("Panthera onca")
            await fetch_taxonomy("panthera onca")

        assert instance.get.call_count == 2  # only first fetch hit network

    @pytest.mark.asyncio
    async def test_expired_cache_re_fetches(self):
        """Entry older than 24 h must trigger a new HTTP fetch."""
        key = "panthera onca"
        old_entry = _CacheEntry(
            taxonomy=GbifTaxonomyData(kingdom="Animalia"),
            source_status="ok",
            cached_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        _cache[key] = old_entry

        fresh_responses = [_mock_response(MATCH_EXACT), _mock_response(DETAIL_WITH_VERNACULAR)]
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=fresh_responses)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            _, status = await fetch_taxonomy("Panthera onca")

        assert instance.get.call_count == 2  # re-fetched
        assert status == "ok"

    @pytest.mark.asyncio
    async def test_not_found_result_is_cached(self):
        """'not_found' results should also be cached to avoid repeated queries."""
        with patch("infrastructure.gbif_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=_mock_response(MATCH_NONE))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await fetch_taxonomy("Xxxxxxxx yyyyyyy")
            await fetch_taxonomy("Xxxxxxxx yyyyyyy")

        # Only 1 HTTP call — second was served from cache
        assert instance.get.call_count == 1
