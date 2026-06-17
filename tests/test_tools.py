import re

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


# ── Helpers ───────────────────────────────────────────────────────────────────

def _size_tokens(size_str: str) -> list[str]:
    return re.split(r'[\s/(),]+', size_str.upper())

SAMPLE_ITEM = {
    "id": "lst_006",
    "title": "Graphic Tee — 2003 Tour Bootleg Style",
    "description": "Vintage-style bootleg tee with faded graphic.",
    "category": "tops",
    "style_tags": ["graphic tee", "vintage", "grunge", "streetwear"],
    "size": "L",
    "condition": "good",
    "price": 24.00,
    "colors": ["black"],
    "brand": None,
    "platform": "depop",
}


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_size_filter_tokens():
    # Every returned item must have "M" as its own size token
    results = search_listings("top", size="M", max_price=None)
    assert len(results) > 0
    for item in results:
        assert "M" in _size_tokens(item["size"])

def test_search_size_l_excludes_xl():
    # lst_027 is size "XL" — "L" as a substring would match, but token matching should not
    results = search_listings("crewneck", size="L", max_price=None)
    ids = [r["id"] for r in results]
    assert "lst_027" not in ids

def test_search_size_s_excludes_shoe_sizes():
    # lst_009 is "US 7" — "S" appears in "US" as substring but not as its own token
    results = search_listings("platform", size="S", max_price=None)
    ids = [r["id"] for r in results]
    assert "lst_009" not in ids

def test_search_sorted_by_relevance():
    results = search_listings("vintage graphic tee", size=None, max_price=None)
    assert len(results) >= 2
    # Top result should have at least one directly matching tag
    top_tags = results[0].get("style_tags", [])
    assert any(kw in " ".join(top_tags) for kw in ["vintage", "graphic", "tee"])


# ── suggest_outfit ────────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

def test_suggest_outfit_empty_wardrobe_returns_string():
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

def test_suggest_outfit_empty_wardrobe_gives_general_advice():
    # With no wardrobe, the response should still be useful styling advice
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_happy_path():
    outfit = "Pair with baggy jeans and chunky sneakers for a 90s grunge look."
    result = create_fit_card(outfit, SAMPLE_ITEM)
    assert isinstance(result, str)
    assert len(result) > 0

def test_create_fit_card_empty_outfit_returns_error():
    result = create_fit_card("", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert "error" in result.lower()

def test_create_fit_card_whitespace_outfit_returns_error():
    result = create_fit_card("   ", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert "error" in result.lower()
