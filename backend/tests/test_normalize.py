import pytest

from app.normalize import normalizeIngredient, normalizeIngredientList, singularize


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2 eggs", "egg"),
        ("1 1/2 cups milk", "milk"),
        ("1/2 tsp salt", "salt"),
        ("0.5 lb ground beef", "beef"),
        ("2-3 cloves garlic, minced", "garlic"),
        ("½ cup sugar", "sugar"),
    ],
)
def testQuantitiesRemoved(raw, expected):
    assert normalizeIngredient(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("3 tablespoons olive oil", "olive oil"),
        ("1 (14 oz) can diced tomatoes", "tomato"),
        ("2 tbsp soy sauce", "soy sauce"),
        ("500 g chicken breasts", "chicken breast"),
        ("1 pinch nutmeg", "nutmeg"),
    ],
)
def testUnitsRemoved(raw, expected):
    assert normalizeIngredient(raw) == expected


@pytest.mark.parametrize(
    "word, expected",
    [
        ("tomatoes", "tomato"),
        ("eggs", "egg"),
        ("berries", "berry"),
        ("peaches", "peach"),
        ("leaves", "leaf"),
        ("onions", "onion"),
        # already singular / uncountable: must not be mangled
        ("asparagus", "asparagus"),
        ("molasses", "molasses"),
        ("hummus", "hummus"),
        ("couscous", "couscous"),
        ("swiss", "swiss"),
        ("glass", "glass"),
        ("rice", "rice"),
    ],
)
def testPluralsHandled(word, expected):
    assert singularize(word) == expected


def testOnlyLastWordSingularized():
    assert normalizeIngredient("Brussels Sprouts") == "brussels sprout"


def testCaseAndPrepWords():
    assert normalizeIngredient("Freshly Chopped CILANTRO Leaves") == "cilantro leaf"


def testEmptyResult():
    assert normalizeIngredient("2 cups") == ""


def testListDedupesAndDropsEmpty():
    raw = ["2 Tomatoes", "1 tomato, diced", "", "1 cup", "Salt"]
    assert normalizeIngredientList(raw) == ["tomato", "salt"]


def testSaltAndPepperSplit():
    raw = ["salt & pepper", "salt and pepper", "2 eggs"]
    assert normalizeIngredientList(raw) == ["salt", "pepper", "egg"]