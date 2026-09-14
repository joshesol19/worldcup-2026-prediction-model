"""
Phase 1c: Join FIFA rankings to matches_with_elo via merge_asof.

Each match gets the most recent ranking snapshot published before that match's
date for both home and away teams.

Rankings source: scraped_data/ subfolder (346 snapshots, 1992-12-31 – 2026-04-01).
Old cumulative CSVs in the parent folder are used only to build the 3-letter
code → full country name lookup table.
"""

import pandas as pd
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# ── 1. Team name canonical map ────────────────────────────────────────────────
name_map = pd.read_csv(PROCESSED / "team_name_map.csv")
alias_to_canonical = dict(zip(name_map["alias"], name_map["canonical"]))


def canon(name: str) -> str:
    return alias_to_canonical.get(name, name)


# ── 2. Build 3-letter code → canonical name lookup from old ranking files ─────
# Old files have country_abrv + country_full; scraped files only have the code
old_files = glob.glob(str(RAW / "fifa_rankings" / "*.csv"))
old_data = pd.concat([pd.read_csv(f) for f in old_files], ignore_index=True)
code_to_name = {
    code: canon(name)
    for code, name in zip(old_data["country_abrv"], old_data["country_full"])
}
print(f"Code→canonical map: {len(code_to_name)} entries")

# ── 3. Load all scraped ranking snapshots ─────────────────────────────────────
scraped_files = glob.glob(str(RAW / "fifa_rankings" / "scraped_data" / "*.csv"))
raw_rank = pd.concat([pd.read_csv(f, parse_dates=["date"]) for f in scraped_files],
                     ignore_index=True)

raw_rank["team"] = raw_rank["country"].map(code_to_name)

# Flag any codes that didn't resolve (should be zero based on pre-check)
unmapped = raw_rank[raw_rank["team"].isna()]["country"].unique()
if len(unmapped):
    print(f"WARNING: unmapped codes: {sorted(unmapped)}")

# Keep only rank ordinal — points span the Aug-2018 methodology break
rankings = (
    raw_rank[["date", "team", "rank"]]
    .rename(columns={"date": "rank_date"})
    .dropna(subset=["team"])
    .sort_values("rank_date")
    .reset_index(drop=True)
)
print(f"Scraped snapshots: {rankings['rank_date'].min().date()} – "
      f"{rankings['rank_date'].max().date()}  "
      f"({rankings['rank_date'].nunique()} dates, {len(rankings):,} rows)")

# ── 3. Load matches ───────────────────────────────────────────────────────────
matches = pd.read_parquet(PROCESSED / "matches_with_elo.parquet")
print(f"\nMatches loaded: {len(matches):,} rows")
print(f"Match date range: {matches['date'].min().date()} – {matches['date'].max().date()}")

matches = matches.sort_values("date").reset_index(drop=True)

# ── 4. merge_asof for home team ───────────────────────────────────────────────
# Rename ranking columns to match home_team key
home_rank = rankings.rename(columns={
    "rank_date": "date",
    "team": "home_team",
    "rank": "home_fifa_rank",
})
matches = pd.merge_asof(
    matches,
    home_rank,
    on="date",
    by="home_team",
    direction="backward",
)

# ── 5. merge_asof for away team ───────────────────────────────────────────────
away_rank = rankings.rename(columns={
    "rank_date": "date",
    "team": "away_team",
    "rank": "away_fifa_rank",
})
matches = pd.merge_asof(
    matches,
    away_rank,
    on="date",
    by="away_team",
    direction="backward",
)

# ── 6. Diagnostics ────────────────────────────────────────────────────────────
print("\n── Null counts after join ────────────────────────────────────────────")
home_null = matches["home_fifa_rank"].isna().sum()
away_null = matches["away_fifa_rank"].isna().sum()
total = len(matches)
print(f"  home_fifa_rank nulls: {home_null:,}  ({home_null/total:.1%})")
print(f"  away_fifa_rank nulls: {away_null:,}  ({away_null/total:.1%})")

# Decompose nulls by year to show where the gaps are
matches["year"] = matches["date"].dt.year
null_by_year = (
    matches[matches["home_fifa_rank"].isna()]
    .groupby("year")
    .size()
    .rename("null_home_rank")
)
if not null_by_year.empty:
    print("\n  Null home ranks by year:")
    print(null_by_year.to_string())

# Show which teams have no rank (appearing in nulls after 1993)
post93_nulls = matches[(matches["date"].dt.year >= 1994) & matches["home_fifa_rank"].isna()]
if not post93_nulls.empty:
    unranked_home = post93_nulls["home_team"].value_counts().head(15)
    print(f"\n  Post-1993 teams with no home rank (top 15):")
    print(unranked_home.to_string())

# Sanity: spot-check a few well-known matches
print("\n── Spot checks ──────────────────────────────────────────────────────")
checks = [
    # 2022 WC final (Argentina vs France)
    ("2022-12-18", "Argentina", "France"),
    # 2018 WC final (France vs Croatia)
    ("2018-07-15", "France", "Croatia"),
    # 2014 WC final (Germany vs Argentina)
    ("2014-07-13", "Germany", "Argentina"),
]
for date, ht, at in checks:
    row = matches[(matches["date"].dt.strftime("%Y-%m-%d") == date) &
                  (matches["home_team"] == ht) &
                  (matches["away_team"] == at)]
    if not row.empty:
        r = row.iloc[0]
        print(f"  {date} {ht} vs {at}:  "
              f"home_rank={r['home_fifa_rank']}  away_rank={r['away_fifa_rank']}  "
              f"home_elo={r['home_elo_pre']:.0f}  away_elo={r['away_elo_pre']:.0f}")
    else:
        print(f"  {date} {ht} vs {at}: NOT FOUND")

# ── 7. Save ───────────────────────────────────────────────────────────────────
matches = matches.drop(columns=["year"])
out_path = PROCESSED / "matches_with_elo_rank.parquet"
matches.to_parquet(out_path, index=False)
print(f"\nSaved → {out_path}")
print(f"Shape: {matches.shape}")
print(f"Columns: {list(matches.columns)}")
