"""
Phase 1a: Build canonical team-name mapping table.

Extracts distinct team names from all four data sources, diffs them,
and outputs data/processed/team_name_map.csv with columns:
  alias, canonical, source_hint

The canonical name convention is Jürisoo's name (it's the spine).
"""

import json
import re
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


# ── 1. Load names from each source ──────────────────────────────────────────

def load_jurisoo_teams():
    df = pd.read_csv(RAW / "jurisoo" / "results.csv")
    teams = set(df["home_team"].dropna()) | set(df["away_team"].dropna())
    return teams

def load_worldcup_teams():
    with open(RAW / "openfootball" / "worldcup.json") as f:
        d = json.load(f)
    # Filter out placeholder strings like "Group A winner", "TBD", etc.
    placeholder_re = re.compile(
        r"(winner|runner|group|tbd|match|loser)", re.IGNORECASE
    )
    teams = set()
    for m in d["matches"]:
        for key in ("team1", "team2"):
            t = m.get(key, "")
            if t and not placeholder_re.search(t):
                teams.add(t)
    return teams

def load_fifa_teams():
    # Use the most recent file available
    ranking_files = sorted((RAW / "fifa_rankings").glob("*.csv"))
    if not ranking_files:
        print("WARNING: no FIFA ranking files found")
        return set()
    df = pd.read_csv(ranking_files[-1])
    return set(df["country_full"].dropna())

def load_transfermarkt_teams():
    df = pd.read_csv(RAW / "transfermarkt" / "national_teams.csv")
    return set(df["name"].dropna())


# ── 2. Manual alias overrides ────────────────────────────────────────────────
# Format: (alias, canonical)  — canonical = Jürisoo name
# Add new entries here as mismatches are discovered.

MANUAL_ALIASES = [
    # Jürisoo uses South Korea; FIFA rankings use Korea Republic
    ("Korea Republic",          "South Korea"),
    # Jürisoo uses North Korea; FIFA uses Korea DPR
    ("Korea DPR",               "North Korea"),
    # Jürisoo uses Turkey; Transfermarkt uses Turkiye
    ("Turkiye",                 "Turkey"),
    # Jürisoo uses Iran; FIFA uses IR Iran
    ("IR Iran",                 "Iran"),
    # Jürisoo uses Ivory Coast; FIFA uses Côte d'Ivoire
    ("Côte d'Ivoire",           "Ivory Coast"),
    # Jürisoo uses Cape Verde; FIFA uses Cabo Verde
    ("Cabo Verde",              "Cape Verde"),
    # Jürisoo uses China PR; Transfermarkt uses China
    ("China",                   "China PR"),
    # worldcup.json uses Bosnia & Herzegovina; Transfermarkt uses Bosnia-Herzegovina
    ("Bosnia & Herzegovina",    "Bosnia and Herzegovina"),
    ("Bosnia-Herzegovina",      "Bosnia and Herzegovina"),
    # FIFA uses Czechia; Jürisoo uses Czech Republic
    ("Czechia",                 "Czech Republic"),
    # worldcup.json and FIFA use USA; Jürisoo uses United States
    ("USA",                     "United States"),
    # FIFA uses Congo DR; Jürisoo uses DR Congo
    ("Congo DR",                "DR Congo"),
    # FIFA uses Curacao (no accent); Jürisoo uses Curaçao
    ("Curacao",                 "Curaçao"),
    # FIFA uses Kyrgyz Republic; Jürisoo uses Kyrgyzstan
    ("Kyrgyz Republic",         "Kyrgyzstan"),
    # FIFA uses The Gambia; Jürisoo uses Gambia
    ("The Gambia",              "Gambia"),
    # FIFA uses Brunei Darussalam; Jürisoo uses Brunei
    ("Brunei Darussalam",       "Brunei"),
    # Chinese Taipei not in Jürisoo — keep FIFA/TM name as canonical for now
    ("Chinese Taipei",          "Chinese Taipei"),
]


# ── 3. Load Jürisoo former_names as additional aliases ───────────────────────

def load_jurisoo_former_names():
    """Returns list of (alias, canonical) from former_names.csv."""
    df = pd.read_csv(RAW / "jurisoo" / "former_names.csv")
    # current = canonical Jürisoo name, former = historical alias
    return [(row["former"], row["current"]) for _, row in df.iterrows()]


# ── 4. Build diff report ─────────────────────────────────────────────────────

def build_diff(jurisoo, worldcup, fifa, transfermarkt):
    """Print mismatches: names in other sources not found in Jürisoo."""
    print("\n=== Names in worldcup.json NOT in Jürisoo ===")
    for t in sorted(worldcup - jurisoo):
        print(f"  {t!r}")

    print("\n=== Names in FIFA rankings NOT in Jürisoo ===")
    for t in sorted(fifa - jurisoo):
        print(f"  {t!r}")

    print("\n=== Names in Transfermarkt NOT in Jürisoo ===")
    for t in sorted(transfermarkt - jurisoo):
        print(f"  {t!r}")

    print("\n=== Names in Jürisoo NOT in worldcup.json (2026 teams only) ===")
    # worldcup.json only has 48 teams — this diff is expected to be large
    # Show only teams that appear in FIFA or Transfermarkt as a cross-check
    j_not_wc = jurisoo - worldcup
    interesting = j_not_wc & (fifa | transfermarkt)
    for t in sorted(interesting):
        print(f"  {t!r}")


# ── 5. Build and save mapping table ─────────────────────────────────────────

def build_map(jurisoo, former_names_aliases, manual_aliases):
    rows = []

    # Every Jürisoo name maps to itself
    for t in sorted(jurisoo):
        rows.append({"alias": t, "canonical": t, "source_hint": "jurisoo_identity"})

    # Historical former names from Jürisoo's own CSV
    for alias, canonical in former_names_aliases:
        rows.append({"alias": alias, "canonical": canonical, "source_hint": "jurisoo_former_names"})

    # Manual overrides
    for alias, canonical in manual_aliases:
        rows.append({"alias": alias, "canonical": canonical, "source_hint": "manual"})

    df = pd.DataFrame(rows).drop_duplicates(subset=["alias"]).sort_values("alias")
    out = PROCESSED / "team_name_map.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} rows to {out}")
    return df


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading team names from all sources...")
    jurisoo      = load_jurisoo_teams()
    worldcup     = load_worldcup_teams()
    fifa         = load_fifa_teams()
    transfermarkt = load_transfermarkt_teams()

    print(f"  Jürisoo:      {len(jurisoo):4d} distinct teams")
    print(f"  worldcup.json:{len(worldcup):4d} distinct teams")
    print(f"  FIFA rankings:{len(fifa):4d} distinct teams")
    print(f"  Transfermarkt:{len(transfermarkt):4d} distinct teams")

    build_diff(jurisoo, worldcup, fifa, transfermarkt)

    former_names_aliases = load_jurisoo_former_names()
    map_df = build_map(jurisoo, former_names_aliases, MANUAL_ALIASES)

    # Spot-check: which 2026 WC teams still have no mapping?
    all_aliases = set(map_df["alias"])
    unresolved = worldcup - all_aliases
    if unresolved:
        print(f"\nWARNING: {len(unresolved)} worldcup.json teams have no mapping:")
        for t in sorted(unresolved):
            print(f"  {t!r}")
    else:
        print("\nAll worldcup.json teams resolved.")
