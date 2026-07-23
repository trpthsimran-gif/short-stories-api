"""
Moral Short Stories API
A REST API serving Panchatantra-style and classic moral short stories.
"""

import json
import random
import re
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Query

WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_HEADERS = {
    "User-Agent": "ShortStoriesAPI/1.0 (educational project)"
}
WIKISOURCE_API_URL = "https://en.wikisource.org/w/api.php"


def extract_sentences(full_text: str) -> list:
    """Break a full Wikipedia article's plain text into clean individual sentence-facts."""
    lines = full_text.split("\n")
    paragraph_lines = [line.strip() for line in lines if len(line.strip()) > 40]
    combined = " ".join(paragraph_lines)
    raw_sentences = re.split(r'(?<=[.!?])\s+', combined)
    sentences = [s.strip() for s in raw_sentences if 30 <= len(s.strip()) <= 500]
    return sentences


def get_wiki_image(topic: str) -> dict:
    """Fetch a live thumbnail image URL for a topic from Wikipedia's summary API."""
    try:
        resp = requests.get(WIKI_SUMMARY_URL + topic.replace(" ", "_"), headers=WIKI_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return {"image_url": None, "wikipedia_url": None}
    thumbnail = (data.get("thumbnail") or {}).get("source")
    page_url = (data.get("content_urls") or {}).get("desktop", {}).get("page")
    return {"image_url": thumbnail, "wikipedia_url": page_url}

app = FastAPI(
    title="Moral Short Stories API",
    description="A REST API serving Panchatantra-style and classic moral short stories, each with a lesson.",
    version="1.0.0"
)

DATA_FILE = Path(__file__).parent / "data" / "stories.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    stories = json.load(f)


@app.get("/", tags=["Root"])
def root():
    """Welcome message and quick guide."""
    return {
        "message": "Welcome to the Moral Short Stories API",
        "total_stories": len(stories),
        "docs": "/docs",
        "endpoints": [
            "/stories",
            "/stories/{story_id}",
            "/stories/random",
            "/stories/search?q=keyword",
            "/origins",
            "/morals"
        ]
    }


@app.get("/stories", tags=["Stories"])
def get_stories(
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Number of results per page"),
    origin: Optional[str] = Query(None, description="Filter by origin e.g. Panchatantra, Aesop's Fables"),
    character: Optional[str] = Query(None, description="Filter by a character appearing in the story")
):
    """Get a paginated list of stories, optionally filtered by origin or character."""
    result = stories

    if origin:
        result = [s for s in result if origin.lower() in s["origin"].lower()]
    if character:
        result = [s for s in result if any(character.lower() in c.lower() for c in s["characters"])]

    total = len(result)
    start = (page - 1) * limit
    end = start + limit
    paginated = result[start:end]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": paginated
    }


@app.get("/stories/random", tags=["Stories"])
def random_story():
    """Get a single random moral story."""
    return random.choice(stories)


@app.get("/stories/search", tags=["Stories"])
def search_stories(q: str = Query(..., min_length=1, description="Keyword to search across title, story, moral, origin, characters, tags")):
    """Search stories by keyword across title, story text, moral, origin, characters, and tags."""
    query = q.lower()
    result = [
        s for s in stories
        if query in s["title"].lower()
        or query in s["story"].lower()
        or query in s["moral"].lower()
        or query in s["origin"].lower()
        or any(query in c.lower() for c in s["characters"])
        or any(query in tag.lower() for tag in s["tags"])
    ]
    return {"query": q, "total": len(result), "results": result}


@app.get("/stories/{story_id}", tags=["Stories"])
def get_story(story_id: int):
    """Get a single story by its ID."""
    for s in stories:
        if s["id"] == story_id:
            return s
    raise HTTPException(status_code=404, detail=f"Story with id {story_id} not found")


@app.get("/origins", tags=["Metadata"])
def get_origins():
    """List all distinct story origins (e.g. Panchatantra, Aesop's Fables)."""
    origins = sorted(set(s["origin"] for s in stories))
    return {"total": len(origins), "origins": origins}


@app.get("/morals", tags=["Metadata"])
def get_morals():
    """List the moral/lesson of every story."""
    morals = [{"id": s["id"], "title": s["title"], "moral": s["moral"]} for s in stories]
    return {"total": len(morals), "morals": morals}


@app.get("/wikisource/search", tags=["Dynamic"])
def wikisource_search(q: str = Query(..., min_length=1, description="A story or collection title to search for, e.g. 'Aesop's Fables', 'The Tortoise and the Hare'")):
    """
    Fetch a REAL classic story/fable text live from Wikisource - not limited to your local 50 stories.
    Wikisource is Wikipedia's sister site hosting full public-domain texts, including many
    classic fable collections like Aesop's Fables, so this can pull genuine original text.
    """
    search_params = {"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 1}

    try:
        search_resp = requests.get(WIKISOURCE_API_URL, params=search_params, headers=WIKI_HEADERS, timeout=10)
        search_resp.raise_for_status()
        search_data = search_resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Could not reach Wikisource: {str(e)}")

    results = search_data.get("query", {}).get("search", [])
    if not results:
        raise HTTPException(status_code=404, detail=f"No Wikisource page found for '{q}'")

    page_title = results[0]["title"]

    extract_params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": page_title,
        "format": "json"
    }

    try:
        extract_resp = requests.get(WIKISOURCE_API_URL, params=extract_params, headers=WIKI_HEADERS, timeout=10)
        extract_resp.raise_for_status()
        extract_data = extract_resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch Wikisource content: {str(e)}")

    pages = extract_data.get("query", {}).get("pages", {})
    page_text = next(iter(pages.values()), {}).get("extract", "")

    return {
        "query": q,
        "title": page_title,
        "text_excerpt": page_text[:2000],
        "full_length_chars": len(page_text),
        "wikisource_url": f"https://en.wikisource.org/wiki/{page_title.replace(' ', '_')}",
        "source": "Wikisource (live)"
    }


@app.get("/wikisource/random", tags=["Dynamic"])
def wikisource_random():
    """
    Get a REAL random short story/text from Wikisource - no search term needed.
    Unlike /wiki/random (which pulls from encyclopedia articles about any topic),
    this pulls from Wikisource's library of actual public-domain literary texts.
    Internally retries up to 8 times to skip thin stubs, chapter fragments, or
    index pages, so you always get back genuine, substantial story content.
    Hit Execute again for a different random text each time.
    """
    max_attempts = 8
    last_error = None

    for _ in range(max_attempts):
        random_params = {"action": "query", "list": "random", "rnnamespace": 0, "rnlimit": 1, "format": "json"}

        try:
            random_resp = requests.get(WIKISOURCE_API_URL, params=random_params, headers=WIKI_HEADERS, timeout=10)
            random_resp.raise_for_status()
            random_data = random_resp.json()
        except requests.RequestException as e:
            last_error = f"Could not reach Wikisource: {str(e)}"
            continue

        random_pages = random_data.get("query", {}).get("random", [])
        if not random_pages:
            last_error = "Wikisource did not return a random page"
            continue

        page_title = random_pages[0]["title"]

        # Skip pages that are clearly not standalone stories (chapter fragments, indexes, disambiguation)
        skip_markers = ["/Chapter", "/Book ", "/Part ", "(disambiguation)", "Index:", "Author:", "Portal:"]
        if any(marker in page_title for marker in skip_markers):
            continue

        extract_params = {"action": "query", "prop": "extracts", "explaintext": 1, "titles": page_title, "format": "json"}

        try:
            extract_resp = requests.get(WIKISOURCE_API_URL, params=extract_params, headers=WIKI_HEADERS, timeout=10)
            extract_resp.raise_for_status()
            extract_data = extract_resp.json()
        except requests.RequestException as e:
            last_error = f"Could not fetch Wikisource content: {str(e)}"
            continue

        pages = extract_data.get("query", {}).get("pages", {})
        page_text = next(iter(pages.values()), {}).get("extract", "")

        # Require substantial real content - long enough to actually be story-like, not a stub
        if page_text and len(page_text.strip()) >= 400:
            return {
                "title": page_title,
                "text_excerpt": page_text[:3000],
                "full_length_chars": len(page_text),
                "wikisource_url": f"https://en.wikisource.org/wiki/{page_title.replace(' ', '_')}",
                "source": "Wikisource (live, random text)"
            }
        # Otherwise loop again and try another random page

    raise HTTPException(
        status_code=503,
        detail=f"Couldn't find a substantial random story after {max_attempts} attempts - please try again. Last issue: {last_error}"
    )
