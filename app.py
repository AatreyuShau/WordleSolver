from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import defaultdict
from typing import List
import requests

DICT_URL = (
    "https://raw.githubusercontent.com/"
    "dwyl/english-words/master/words_alpha.txt"
)

API_VERSION = "2.0-grid-colors"

app = FastAPI(
    title="Wordle Solver API",
    version=API_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORDS_BY_LENGTH = defaultdict(list)
DICTIONARY_LOADED = False


def load_dictionary():
    global DICTIONARY_LOADED

    print("Loading dictionary...")

    try:
        response = requests.get(
            DICT_URL,
            timeout=30
        )

        response.raise_for_status()

        for word in response.text.splitlines():

            word = word.strip().lower()

            if word.isalpha():
                WORDS_BY_LENGTH[len(word)].append(word)

        DICTIONARY_LOADED = True

        total = sum(
            len(v)
            for v in WORDS_BY_LENGTH.values()
        )

        print(
            f"Loaded {total} words."
        )

    except Exception as e:
        print(
            f"Dictionary load failed: {e}"
        )


load_dictionary()


class SolveRequest(BaseModel):
    grid: List[List[str]]
    colors: List[List[str]]


def wordle_filter(
    words,
    greens,
    yellows,
    min_freq,
    max_freq
):
    results = []

    for word in words:

        valid = True

        # Green letters

        for index, letter in greens.items():

            if word[index] != letter:
                valid = False
                break

        if not valid:
            continue

        # Yellow letters

        for letter, banned_positions in yellows.items():

            if letter not in word:
                valid = False
                break

            for pos in banned_positions:

                if word[pos] == letter:
                    valid = False
                    break

        if not valid:
            continue

        # Minimum occurrences

        for letter, count in min_freq.items():

            if word.count(letter) < count:
                valid = False
                break

        if not valid:
            continue

        # Maximum occurrences

        for letter, count in max_freq.items():

            if word.count(letter) > count:
                valid = False
                break

        if not valid:
            continue

        results.append(word)

    return results


def analyze_grid(grid, colors):

    rows = len(grid)

    if rows == 0:
        return []

    cols = len(grid[0])

    greens = {}

    yellows = defaultdict(set)

    row_min = defaultdict(
        lambda: defaultdict(int)
    )

    row_gray = defaultdict(set)

    for r in range(rows):

        for c in range(cols):

            letter = grid[r][c]

            if not letter:
                continue

            letter = letter.lower()

            color = colors[r][c]

            if color == "green":

                greens[c] = letter
                row_min[r][letter] += 1

            elif color == "yellow":

                yellows[letter].add(c)
                row_min[r][letter] += 1

            else:

                row_gray[r].add(letter)

    min_freq = defaultdict(int)

    max_freq = defaultdict(
        lambda: float("inf")
    )

    for r in range(rows):

        for letter, count in row_min[r].items():

            min_freq[letter] = max(
                min_freq[letter],
                count
            )

        for letter in row_gray[r]:

            if letter in row_min[r]:

                max_freq[letter] = min(
                    max_freq[letter],
                    row_min[r][letter]
                )

            else:

                max_freq[letter] = 0

    words = WORDS_BY_LENGTH.get(
        cols,
        []
    )

    return wordle_filter(
        words,
        greens,
        yellows,
        min_freq,
        max_freq
    )


@app.get("/")
def root():
    return {
        "status": "ok",
        "version": API_VERSION,
        "dictionary_loaded": DICTIONARY_LOADED
    }


@app.get("/version")
def version():
    return {
        "version": API_VERSION
    }


@app.get("/health")
def health():
    return {
        "healthy": DICTIONARY_LOADED,
        "word_lengths": len(
            WORDS_BY_LENGTH
        )
    }


@app.post("/solve")
def solve(req: SolveRequest):

    if not DICTIONARY_LOADED:
        raise HTTPException(
            status_code=503,
            detail="Dictionary not loaded."
        )

    if not req.grid:
        raise HTTPException(
            status_code=400,
            detail="Grid is empty."
        )

    words = analyze_grid(
        req.grid,
        req.colors
    )

    return {
        "count": len(words),
        "words": words[:500]
    }