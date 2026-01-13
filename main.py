from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import defaultdict
import requests

DICT_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"

app = FastAPI(title="Wordle Solver API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins (safe for local dev)
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
    greens: dict[int, str]
    yellows: dict[str, list[int]]
    grays: list[str]
    min_freq: dict[str, int]
    length: int

##

def solve(req: SolveRequest):
    results = []

    for w in WORDS_BY_LENGTH[req.length]:
        ok = True

        # greens
        for i, ch in req.greens.items():
            if w[i] != ch:
                ok = False
                break
        if not ok: continue

        # grays
        for ch in req.grays:
            if ch in w:
                ok = False
                break
        if not ok: continue

        # yellos
        for ch, banned in req.yellows.items():
            if ch not in w:
                ok = False
                break
            for i in banned:
                if w[i] == ch:
                    ok = False
                    break
        if not ok: continue

        # min freq
        for ch, count in req.min_freq.items():
            if w.count(ch) < count:
                ok = False
                break

        if ok:
            results.append(w)

    return results

# --------
@app.post("/solve")
def solve_wordle(req: SolveRequest):
    words = solve(req)
    return {
        "count": len(words),
        "words": words[:500] # safety cap
    }
