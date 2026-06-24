from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import defaultdict
import requests

DICT_URL = (
    "https://raw.githubusercontent.com/"
    "dwyl/english-words/master/words_alpha.txt"
)

app = FastAPI(title="Wordle Solver API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORDS_BY_LENGTH = defaultdict(list)


def load_dictionary():

    print("Loading dictionary...")

    text = requests.get(DICT_URL).text.splitlines()

    for w in text:

        w = w.strip().lower()

        if w.isalpha():
            WORDS_BY_LENGTH[len(w)].append(w)

    print("Dictionary loaded.")


load_dictionary()


class SolveRequest(BaseModel):
    grid: list[list[str]]
    colors: list[list[str]]


def wordle_filter(
    words,
    greens,
    yellows,
    min_freq,
    max_freq
):

    results = []

    for w in words:

        ok = True

        # greens

        for i, ch in greens.items():

            if w[i] != ch:
                ok = False
                break

        if not ok:
            continue

        # yellows

        for ch, banned in yellows.items():

            if ch not in w:
                ok = False
                break

            for pos in banned:

                if w[pos] == ch:
                    ok = False
                    break

        if not ok:
            continue

        # minimum counts

        for ch, count in min_freq.items():

            if w.count(ch) < count:
                ok = False
                break

        if not ok:
            continue

        # maximum counts

        for ch, count in max_freq.items():

            if w.count(ch) > count:
                ok = False
                break

        if not ok:
            continue

        results.append(w)

    return results


def analyze_grid(grid, colors):

    rows = len(grid)
    cols = len(grid[0])

    greens = {}

    yellows = defaultdict(set)

    row_min = defaultdict(
        lambda: defaultdict(int)
    )

    row_gray = defaultdict(set)

    for r in range(rows):

        for c in range(cols):

            ch = grid[r][c]

            if not ch:
                continue

            color = colors[r][c]

            if color == "green":

                greens[c] = ch

                row_min[r][ch] += 1

            elif color == "yellow":

                yellows[ch].add(c)

                row_min[r][ch] += 1

            else:

                row_gray[r].add(ch)

    min_freq = defaultdict(int)

    max_freq = defaultdict(
        lambda: float("inf")
    )

    for r in range(rows):

        for ch, cnt in row_min[r].items():

            min_freq[ch] = max(
                min_freq[ch],
                cnt
            )

        for ch in row_gray[r]:

            if ch in row_min[r]:

                max_freq[ch] = min(
                    max_freq[ch],
                    row_min[r][ch]
                )

            else:

                max_freq[ch] = 0

    words = WORDS_BY_LENGTH[cols]

    return wordle_filter(
        words,
        greens,
        yellows,
        min_freq,
        max_freq
    )


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/solve")
def solve(req: SolveRequest):

    words = analyze_grid(
        req.grid,
        req.colors
    )

    return {
        "count": len(words),
        "words": words[:500]
    }
