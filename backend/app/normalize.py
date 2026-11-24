"""Ingredient normalization shared by ingestion (Phase 1) and grounding (Phase 3).

"2 1/2 cups Chopped Tomatoes (fresh)" -> "tomato"

Rules, applied in order:
  1. lowercase, drop parentheticals and anything after a comma ("onion, diced" -> "onion")
  2. strip quantities: integers, decimals, fractions (1/2), unicode fractions, ranges (2-3)
  3. strip units (cup, tbsp, oz, ...) and common prep words (chopped, minced, ...)
  4. singularize simple plurals on the last word only (tomatoes -> tomato, berries -> berry)
"""

import re

UNITS = {
    "cup", "cups", "c", "tablespoon", "tablespoons", "tbsp", "tbs", "tbsps", "t",
    "teaspoon", "teaspoons", "tsp", "tsps", "ounce", "ounces", "oz", "pound", "pounds",
    "lb", "lbs", "gram", "grams", "g", "kilogram", "kilograms", "kg", "milliliter",
    "milliliters", "ml", "liter", "liters", "l", "pint", "pints", "pt", "quart", "quarts",
    "qt", "gallon", "gallons", "gal", "pinch", "pinches", "dash", "dashes", "clove",
    "cloves", "can", "cans", "package", "packages", "pkg", "jar", "jars", "bunch",
    "bunches", "slice", "slices", "stick", "sticks", "sprig", "sprigs", "head", "heads",
    "piece", "pieces", "container", "containers", "bottle", "bottles", "box", "boxes",
    "bag", "bags", "envelope", "envelopes", "handful", "handfuls", "inch", "inches",
}

PREP_WORDS = {
    "chopped", "minced", "diced", "sliced", "grated", "shredded", "crushed", "ground",
    "fresh", "freshly", "finely", "coarsely", "roughly", "thinly", "large", "medium",
    "small", "whole", "peeled", "seeded", "cored", "softened", "melted", "beaten",
    "divided", "packed", "to", "taste", "of", "a", "an", "about", "optional", "cubed",
    "halved", "quartered", "trimmed", "rinsed", "drained", "cooked", "uncooked", "raw",
    "frozen", "thawed", "room", "temperature", "lightly", "heaping", "level", "and", "or",
    "firmly", "sifted", "reserved",
}

# words ending in "s" that are already singular (or uncountable)
NO_SINGULARIZE = {
    "asparagus", "molasses", "hummus", "couscous", "swiss", "citrus", "grits", "oats",
    "brussels", "greens", "hummous", "bass", "watercress", "schnapps", "jus",
}

IRREGULAR = {"leaves": "leaf", "loaves": "loaf", "halves": "half", "knives": "knife"}

UNICODE_FRACTIONS = "¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞"

quantityPattern = re.compile(
    rf"(\d+\s*[-–]\s*\d+|\d+\s+\d+/\d+|\d+/\d+|\d*\.\d+|\d+|[{UNICODE_FRACTIONS}])"
)
nonLetterPattern = re.compile(r"[^a-z\s-]")
whitespacePattern = re.compile(r"\s+")


def singularize(word: str) -> str:
    """Singularize a simple English plural. Deliberately conservative."""
    if word in NO_SINGULARIZE or len(word) <= 3:
        return word
    if word in IRREGULAR:
        return IRREGULAR[word]
    if word.endswith("ies"):
        return word[:-3] + "y"  # berries -> berry
    if word.endswith(("oes", "ches", "shes", "sses", "xes", "zes")):
        return word[:-2]  # tomatoes -> tomato, peaches -> peach
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]  # eggs -> egg
    return word


def normalizeIngredient(rawIngredient: str) -> str:
    """Return a canonical ingredient name, or "" if nothing is left."""
    text = rawIngredient.lower()
    text = re.sub(r"\([^)]*\)", " ", text)  # drop "(14 oz)" style notes
    text = text.split(",")[0]  # "onion, diced" -> "onion"
    text = quantityPattern.sub(" ", text)
    text = nonLetterPattern.sub(" ", text)
    words = [w.strip("-") for w in whitespacePattern.split(text)]
    words = [w for w in words if w and w not in UNITS and w not in PREP_WORDS]
    if not words:
        return ""
    words[-1] = singularize(words[-1])
    return " ".join(words)


# "salt & pepper" / "salt and pepper" collapse to "salt pepper"; these are really two items.
COMBINED_ITEMS = {"salt pepper": ["salt", "pepper"], "salt black pepper": ["salt", "black pepper"]}


def normalizeIngredientList(rawIngredients: list[str]) -> list[str]:
    """Normalize a list, dropping empties and duplicates while keeping order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in rawIngredients:
        name = normalizeIngredient(raw)
        for item in COMBINED_ITEMS.get(name, [name]):
            if item and item not in seen:
                seen.add(item)
                result.append(item)
    return result