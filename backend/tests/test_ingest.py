import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ingestRecipes import (  # noqa: E402
    cleanRow,
    loadCleanRecipes,
    minutesFromTimeTags,
    parseListField,
)

HEADER = ["id", "name", "description", "ingredients", "ingredients_raw", "steps",
          "servings", "serving_size", "tags"]


def makeRow(recipeId=1, name="Cherry Cobbler", rawIngredients=None, steps=None, tags=None):
    return {
        "id": recipeId,
        "name": name,
        "ingredients_raw": json.dumps(rawIngredients or ["2 eggs", "1/2 cup sugar"]),
        "steps": json.dumps(steps or ["Mix.", "Bake."]),
        "tags": json.dumps(tags or ["60-minutes-or-less", "american", "desserts"]),
    }


def writeCsv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
    return path


def testCleanRowNormalizesEverything():
    recipe = cleanRow(makeRow(rawIngredients=["2 (21 ounce) cans cherry pie filling", "2 eggs"]))
    assert recipe["ingredients"] == ["cherry pie filling", "egg"]
    assert recipe["cookMinutes"] == 60
    assert recipe["tags"] == ["american"]  # "desserts" isn't a diet/cuisine tag


def testCleanRowRejectsMissingSteps():
    row = makeRow()
    row["steps"] = "[]"
    assert cleanRow(row) is None


def testTightestTimeTagWins():
    assert minutesFromTimeTags(["60-minutes-or-less", "30-minutes-or-less"]) == 30
    assert minutesFromTimeTags(["desserts"]) is None


def testParseRepairsApostrophes():
    assert parseListField('["Heat but don"t boil.", "Serve."]') == ["Heat but don't boil.", "Serve."]


def testParseRepairsInchMarks():
    broken = '["Grease a 9" dish.", "Drop 1" apart."]'
    assert parseListField(broken) == ['Grease a 9" dish.', 'Drop 1" apart.']


def testParseGivesUpOnGarbage():
    assert parseListField("not a list") == []
    assert parseListField(float("nan")) == []


def testDuplicateIdsSkippedAndLimitRespected(tmp_path):
    rows = [makeRow(recipeId=1), makeRow(recipeId=1), makeRow(recipeId=2), makeRow(recipeId=3)]
    csvFile = writeCsv(tmp_path / "recipes.csv", rows)
    recipes, skipped = loadCleanRecipes(csvFile, limit=2)
    assert [r["id"] for r in recipes] == [1, 2]
    assert skipped == 1