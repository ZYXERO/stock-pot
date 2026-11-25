"""Clean recipes from the Food.com dataset and load them into Postgres.

Usage (from backend/):
    python scripts/ingestRecipes.py --limit 10000 --dry-run   # clean and report only
    python scripts/ingestRecipes.py --limit 10000             # clean and upsert into Supabase

Expects data/raw/recipes_ingredients.csv with columns:
    id, name, ingredients_raw, steps, tags (plus a few we ignore)
"""

import argparse
import ast
import json
import re
import sys
import warnings
from pathlib import Path

import pandas as pd

# Let this script import from app/ when run as `python scripts/ingestRecipes.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.normalize import normalizeIngredientList  # noqa: E402

DEFAULT_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "recipes_ingredients.csv"

# Only diet and cuisine tags are kept; the dataset has hundreds of noisy tags otherwise.
ALLOWED_TAGS = {
    "vegetarian", "vegan", "gluten-free", "dairy-free", "egg-free", "nut-free",
    "low-carb", "low-fat", "low-sodium", "low-calorie", "high-protein", "kosher",
    "italian", "mexican", "chinese", "indian", "thai", "japanese", "korean",
    "vietnamese", "french", "greek", "spanish", "middle-eastern", "mediterranean",
    "american", "southern-united-states", "cajun", "caribbean", "african", "german",
    "asian", "european",
}

# No minutes column in this dataset, only time tags. Each tag is an upper bound, so
# cookMinutes stores the tightest one: still correct for a `cook_minutes <= maxMinutes` filter.
TIME_TAG_MINUTES = {
    "15-minutes-or-less": 15,
    "30-minutes-or-less": 30,
    "60-minutes-or-less": 60,
    "4-hours-or-less": 240,
}

# A quote between two letters was an apostrophe: don"t -> don't
apostrophePattern = re.compile(r'(?<=[A-Za-z])"(?=[A-Za-z])')
# Any other quote not in a JSON delimiter position ([" , ", "]) is text, like 9" pan
strayQuotePattern = re.compile(r'(?<!\[)(?<!, )"(?!, ")(?!\]$)')


def repairQuotes(text: str) -> str:
    """Fix bare double quotes inside strings that break JSON."""
    text = apostrophePattern.sub("'", text.strip())
    return strayQuotePattern.sub(r'\\"', text)


def parseListField(value) -> list[str]:
    """The CSV stores lists as JSON strings. Try three parsers, cheapest first; give up with []."""
    if not isinstance(value, str) or not value.strip():
        return []
    parsers = (
        json.loads,  # well-formed rows
        lambda text: json.loads(repairQuotes(text)),  # bare apostrophes / inch marks
        ast.literal_eval,  # Python-literal syntax rescues a few more quoting quirks
    )
    for parse in parsers:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                parsed = parse(value)
        except (ValueError, SyntaxError):
            continue
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def cleanSteps(rawSteps: list[str]) -> list[str]:
    return [step.strip() for step in rawSteps if step and step.strip()]


def cleanTags(rawTags: list[str]) -> list[str]:
    return sorted({tag.strip().lower() for tag in rawTags} & ALLOWED_TAGS)


def minutesFromTimeTags(rawTags: list[str]) -> int | None:
    bounds = [TIME_TAG_MINUTES[tag] for tag in rawTags if tag in TIME_TAG_MINUTES]
    return min(bounds) if bounds else None


def cleanRow(row: dict) -> dict | None:
    """One CSV row -> one clean recipe dict, or None if it's missing essentials.
    Uses ingredients_raw: the dataset's pre-cleaned `ingredients` column drops
    items like eggs, sugar and salt in most rows."""
    rawTags = parseListField(row.get("tags"))
    recipe = {
        "id": int(row["id"]),
        "title": str(row.get("name") or "").strip(),
        "ingredients": normalizeIngredientList(parseListField(row.get("ingredients_raw"))),
        "steps": cleanSteps(parseListField(row.get("steps"))),
        "cookMinutes": minutesFromTimeTags(rawTags),
        "tags": cleanTags(rawTags),
    }
    if not (recipe["title"] and recipe["ingredients"] and recipe["steps"]):
        return None
    return recipe


def loadCleanRecipes(filePath: Path, limit: int) -> tuple[list[dict], int]:
    """Read rows until `limit` valid recipes with unique ids are collected.
    Returns (recipes, rowsSkipped). Duplicate ids are skipped because the file
    has exact duplicate rows, and Postgres rejects a batch that repeats an id."""
    recipes: list[dict] = []
    seenIds: set[int] = set()
    skipped = 0
    for chunk in pd.read_csv(filePath, chunksize=5000):
        for row in chunk.to_dict("records"):
            recipe = cleanRow(row)
            if recipe is None or recipe["id"] in seenIds:
                skipped += 1
                continue
            seenIds.add(recipe["id"])
            recipes.append(recipe)
            if len(recipes) >= limit:
                return recipes, skipped
    return recipes, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and load Food.com recipes.")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="dataset CSV")
    parser.add_argument("--limit", type=int, default=10000, help="number of recipes to load")
    parser.add_argument("--dry-run", action="store_true", help="clean and report without writing")
    args = parser.parse_args()

    if not args.file.exists():
        raise SystemExit(f"Dataset not found: {args.file}")

    recipes, skipped = loadCleanRecipes(args.file, args.limit)
    print(f"Cleaned {len(recipes)} recipes (skipped {skipped} rows)")
    if recipes:
        print("Sample:", json.dumps(recipes[0], indent=2, ensure_ascii=False)[:800])

    if args.dry_run:
        print("Dry run: nothing written.")
        return

    from app.db import upsertRecipes

    written = upsertRecipes(recipes)
    print(f"Upserted {written} rows into recipes.")


if __name__ == "__main__":
    main()