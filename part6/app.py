#!/usr/bin/env python3
"""
Part 6 starter CLI.

WHAT'S NEW IN PART 6
- Fetch Shakespeare's sonnets from the PoetryDB API:
    https://poetrydb.org/author,title/Shakespeare;Sonnet
- Cache the downloaded sonnets in a local JSON file so the API is not hit every run.
- Measure and print timing information:
    * How long it takes to load the sonnets (from API or cache)
    * How long each user query takes to be evaluated.

As before:
- Reuse your search functionality from earlier parts.
- Reuse your config handling and search mode implementation from Part 5.
"""

from typing import List, Dict, Any
import json
import os
import time
import urllib.request
import urllib.error
import pprint

from .constants import BANNER, HELP, POETRYDB_URL

CACHE_FILENAME = "sonnets.json"


# ---------- Search helpers (unchanged from Part 5) ----------

def find_spans(text: str, pattern: str):
    """Return [(start, end), ...] for all (possibly overlapping) matches.
    Inputs should already be lowercased by the caller."""
    spans = []
    if not pattern:
        return spans

    for i in range(len(text) - len(pattern) + 1):
        if text[i:i + len(pattern)] == pattern:
            spans.append((i, i + len(pattern)))
    return spans


def ansi_highlight(text: str, spans):
    """Return text with ANSI highlight escape codes inserted."""
    if not spans:
        return text

    spans = sorted(spans)
    merged = []

    # Merge overlapping spans
    current_start, current_end = spans[0]
    for s, e in spans[1:]:
        if s <= current_end:
            current_end = max(current_end, e)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = s, e
    merged.append((current_start, current_end))

    # Build highlighted string
    out = []
    i = 0
    for s, e in merged:
        out.append(text[i:s])
        out.append("\033[43m\033[30m")  # yellow background, black text
        out.append(text[s:e])
        out.append("\033[0m")           # reset
        i = e
    out.append(text[i:])
    return "".join(out)


def search_sonnet(sonnet: Dict[str, Any], query: str) -> Dict[str, Any]:
    title_raw = str(sonnet["title"])
    lines_raw = sonnet["lines"]  # list[str]

    q = query.lower()
    title_spans = find_spans(title_raw.lower(), q)

    line_matches = []
    for idx, line_raw in enumerate(lines_raw, start=1):  # 1-based line numbers
        spans = find_spans(line_raw.lower(), q)
        if spans:
            line_matches.append(
                {"line_no": idx, "text": line_raw, "spans": spans}
            )

    total = len(title_spans) + sum(len(lm["spans"]) for lm in line_matches)
    return {
        "title": title_raw,
        "title_spans": title_spans,
        "line_matches": line_matches,
        "matches": total,
    }


def combine_results(result1: Dict[str, Any], result2: Dict[str, Any]) -> Dict[str, Any]:
    """Combine two result dicts (used for AND-mode)."""
    combined = dict(result1)  # shallow copy

    combined["matches"] = result1["matches"] + result2["matches"]
    combined["title_spans"] = sorted(
        result1["title_spans"] + result2["title_spans"]
    )

    # Merge line_matches by line number
    lines_by_no = {lm["line_no"]: dict(lm) for lm in result1["line_matches"]}
    for lm in result2["line_matches"]:
        ln = lm["line_no"]
        if ln in lines_by_no:
            # extend spans & keep original text
            lines_by_no[ln]["spans"].extend(lm["spans"])
        else:
            lines_by_no[ln] = dict(lm)

    combined["line_matches"] = sorted(
        lines_by_no.values(), key=lambda lm: lm["line_no"]
    )

    return combined


def print_results(
    query: str,
    results: List[Dict[str, Any]],
    highlight: bool,
    query_time_ms: float | None = None,
) -> None:
    total_docs = len(results)
    matched = [r for r in results if r["matches"] > 0]

    line = f'{len(matched)} out of {total_docs} sonnets contain "{query}".'
    if query_time_ms is not None:
        line += f" Your query took {query_time_ms:.2f}ms."
    print(line)

    for idx, r in enumerate(matched, start=1):
        title_line = (
            ansi_highlight(r["title"], r["title_spans"])
            if highlight
            else r["title"]
        )
        print(f"\n[{idx}/{total_docs}] {title_line}")
        for lm in r["line_matches"]:
            line_out = (
                ansi_highlight(lm["text"], lm["spans"])
                if highlight
                else lm["text"]
            )
            print(f"  [{lm['line_no']:2}] {line_out}")


# ---------- Paths & data loading ----------

def module_relative_path(name: str) -> str:
    """Return absolute path for a file next to this module."""
    return os.path.join(os.path.dirname(__file__), name)


def fetch_sonnets_from_api() -> List[Dict[str, Any]]:
    """ToDo 1:
    Call the PoetryDB API (POETRYDB_URL), decode the JSON response and
    convert it into a list of dicts.

    - Use only the standard library (urllib.request).
    - PoetryDB returns a list of poems.
    - You can add error handling: raise a RuntimeError (or print a helpful message) if something goes wrong.
    """
    sonnets = {}

    with urllib.request.urlopen(POETRYDB_URL) as response:
        try:
            sonnets = json.load(response)
        except json.decoder.JSONDecodeError:
            raise RuntimeError("Invalid json.load() argument.")


    return sonnets


def load_sonnets() -> List[Dict[str, Any]]:
    """ToDo 2:

    Load Shakespeare's sonnets with caching.

    Behaviour:
      1. If 'sonnets.json' already exists:
           - Print: "Loaded sonnets from cache."
           - Return the data.
      2. Otherwise:
           - Call fetch_sonnets_from_api() to load the data.
           - Print: "Downloaded sonnets from PoetryDB."
           - Save the data (pretty-printed) to CACHE_FILENAME.
           - Return the data.
    """
    sonnets_path = module_relative_path(CACHE_FILENAME)

    if os.path.exists(sonnets_path):
        with open(sonnets_path) as f:
            sonnets = json.load(f)
        print("Loaded sonnets from the cache.")
    else:
        sonnets = fetch_sonnets_from_api()
        with open(sonnets_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(sonnets, indent=2, ensure_ascii=False))
        print("Downloaded sonnets from PoetryDB.")

    # Default implementation: Load from the API always

    return sonnets

# ---------- Config handling (carry over from Part 5) ----------

DEFAULT_CONFIG = {"highlight": True, "search_mode": "AND"}

def load_config() -> Dict[str, Any]:
    """ToDo 0:
    Copy your working implementation from Part 5.
    """
    config = {}
    path = module_relative_path("config.json")
    config_defaults = DEFAULT_CONFIG.copy()

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                tmp = json.load(f)
            except json.decoder.JSONDecodeError:
                tmp = {}
    else:
        return config_defaults

    for x in config_defaults.keys():
        if x in tmp:
            config[x] = tmp[x]
        else:
            config[x] = config_defaults[x]

    return config


def save_config(cfg: Dict[str, Any]) -> None:
    """ToDo 0:
    Copy your working implementation from Part 5.
    """
    tmp = {}
    path = module_relative_path("config.json")

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                tmp = json.load(f)
            except json.decoder.JSONDecodeError:
                tmp = {}

        for x in cfg.keys():
            tmp[x] = cfg[x]

    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(tmp, indent=2, ensure_ascii=False))


# ---------- CLI loop ----------

def main() -> None:
    print(BANNER)
    config = load_config()

    # Load sonnets (from cache or API
    # ToDo 3: Time how long loading the sonnets take and print it to the console
    start = time.perf_counter()
    sonnets = load_sonnets()
    end = time.perf_counter()

    elapsed = (end - start) * 1000
    print(f"Elapsed time: {elapsed:.3f} [ms]")

    print(f"Loaded {len(sonnets)} sonnets.")

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not raw:
            continue

        # commands
        if raw.startswith(":"):
            if raw == ":quit":
                print("Bye.")
                break

            if raw == ":help":
                print(HELP)
                continue

            if raw.startswith(":highlight"):
                parts = raw.split()
                if len(parts) == 2 and parts[1].lower() in ("on", "off"):
                    config["highlight"] = parts[1].lower() == "on"
                    print("Highlighting", "ON" if config["highlight"] else "OFF")
                    # ToDo 5: call save_config(config) here so the choice persists.
                else:
                    print("Usage: :highlight on|off")
                continue

            if raw.startswith(":search-mode"):
                parts = raw.split()
                if len(parts) == 2 and parts[1].upper() in ("AND", "OR"):
                    config["search_mode"] = parts[1].upper()
                    print("Search mode set to", config["search_mode"])
                    save_config(config)
                else:
                    print("Usage: :search-mode AND|OR")
                continue

            print("Unknown command. Type :help for commands.")
            continue

        # ---------- Query evaluation ----------
        words = raw.split()
        if not words:
            continue

        # ToDo 3: Time how the execution of the user query takes
        start = time.perf_counter()
        # query
        combined_results = []

        words = raw.split()

        for word in words:
            # Searching for the word in all sonnets
            results = [search_sonnet(s, word) for s in sonnets]

            if not combined_results:
                # No results yet. We store the first list of results in combined_results
                combined_results = results
            else:
                # We have an additional result, we have to merge the two results: loop all sonnets
                for i in range(len(combined_results)):
                    # Checking each sonnet individually
                    combined_result = combined_results[i]
                    result = results[i]

                    if config["search_mode"] == "AND":
                        if combined_result["matches"] > 0 and result["matches"] > 0:
                            # Only if we have matches in both results, we consider the sonnet (logical AND!)
                            combined_results[i] = combine_results(combined_result, result)
                        else:
                            # Not in both. No match!
                            combined_result["matches"] = 0
                    elif config["search_mode"] == "OR":
                        combined_results[i] = combine_results(combined_result, result)

        # Initialize elapsed_ms to contain the number of milliseconds the query evaluation took
        elapsed_ms = 0

        print_results(raw, combined_results, bool(config.get("highlight", True)), elapsed_ms)
        end = time.perf_counter()

        elapsed = (end - start) * 1000
        print(f"Elapsed time: {elapsed:.3f} [ms]")

if __name__ == "__main__":
    main()
