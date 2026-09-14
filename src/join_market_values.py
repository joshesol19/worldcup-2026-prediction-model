"""
Phase 1d: Join Transfermarkt squad market values to matches.

Approach: country_of_citizenship as national team proxy (0.1% mismatch rate
for players with known national teams — confirmed accurate).

Squad value = sum of top-23 player market values by citizenship as of match date.
Computed event-driven over valuation history to avoid a 47M-row cross-join.

KNOWN LIMITATIONS (documented, not papered over):
1. Pre-2004 coverage: Transfermarkt valuations essentially start in 2004.
   Matches before 2004 will have null squad values (~14 years of the 36-year window).
2. Citizenship proxy: uses country_of_citizenship, not actual national team eligibility.
   Mismatch rate is 0.1% for players with known national teams. For historical
   players without current_national_team_id set, unknown — but directionally sound.
3. Top-23 is a proxy for a matchday squad. It captures squad depth but not
   the actual 23 called up. Good enough for a team-strength feature.
4. Small/non-UEFA confederations: sparser player pools in Transfermarkt database
   → squad values will be underestimated for CAF, AFC, CONCACAF outside top nations.
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# ── 1. Canonical name map ─────────────────────────────────────────────────────
name_map = pd.read_csv(PROCESSED / "team_name_map.csv")
alias_to_canonical = dict(zip(name_map["alias"], name_map["canonical"]))


def canon(name: str) -> str:
    return alias_to_canonical.get(name, name)


# ── 2. Load players — get player_id → canonical citizenship ──────────────────
players = pd.read_csv(RAW / "transfermarkt" / "players.csv",
                      usecols=["player_id", "country_of_citizenship"])
players["citizenship"] = players["country_of_citizenship"].map(canon)
players = players.dropna(subset=["citizenship"])

pid_to_cit = dict(zip(players["player_id"], players["citizenship"]))

# citizenship → set of player_ids (for fast lookup)
cit_to_pids: dict[str, set] = defaultdict(set)
for pid, cit in pid_to_cit.items():
    cit_to_pids[cit].add(pid)

print(f"Players loaded: {len(players):,}  |  unique citizenships: {players['citizenship'].nunique()}")

# ── 3. Load valuations ────────────────────────────────────────────────────────
vals = pd.read_csv(
    RAW / "transfermarkt" / "player_valuations.csv",
    usecols=["player_id", "date", "market_value_in_eur"],
    parse_dates=["date"],
)
# Drop players with no citizenship mapping
vals = vals[vals["player_id"].isin(pid_to_cit)].copy()
vals = vals.sort_values("date").reset_index(drop=True)

print(f"Valuations loaded: {len(vals):,}  |  date range: "
      f"{vals['date'].min().date()} – {vals['date'].max().date()}")
print(f"Unique players with valuations: {vals['player_id'].nunique():,}")

# ── 4. Event-driven squad value computation ───────────────────────────────────
# Walk through valuations chronologically. Maintain:
#   current_values: {player_id: latest_known_market_value}
#   At each batch of valuation updates, recompute squad value for affected
#   citizenships and record a (citizenship, date, squad_value) row.
# This avoids a 47M-row cross-join and is O(n_valuations).

current_values: dict[int, float] = {}   # player_id → current value
squad_value_records: list[dict] = []

for val_date, batch in vals.groupby("date", sort=True):
    affected_citizenships: set[str] = set()

    for _, row in batch.iterrows():
        pid = row["player_id"]
        val = row["market_value_in_eur"]
        current_values[pid] = val
        cit = pid_to_cit.get(pid)
        if cit:
            affected_citizenships.add(cit)

    # Recompute squad value for each affected citizenship
    for cit in affected_citizenships:
        player_values = [
            current_values[pid]
            for pid in cit_to_pids[cit]
            if pid in current_values
        ]
        if not player_values:
            continue
        top23_sum = float(np.partition(player_values, -min(23, len(player_values)))
                          [-min(23, len(player_values)):].sum()
                          if len(player_values) >= 23
                          else sum(player_values))
        squad_value_records.append({
            "team": cit,
            "date": val_date,
            "squad_value": top23_sum,
        })

squad_values = (
    pd.DataFrame(squad_value_records)
    .sort_values(["team", "date"])
    .reset_index(drop=True)
)
print(f"\nSquad value snapshots: {len(squad_values):,}  "
      f"({squad_values['team'].nunique()} teams  |  "
      f"{squad_values['date'].nunique()} unique dates)")

# ── 5. Load matches and merge_asof ────────────────────────────────────────────
matches = pd.read_parquet(PROCESSED / "matches_with_elo_rank.parquet")
matches = matches.sort_values("date").reset_index(drop=True)
print(f"\nMatches loaded: {len(matches):,}")

def add_squad_value(matches: pd.DataFrame, squad_values: pd.DataFrame,
                    team_col: str, value_col: str) -> pd.DataFrame:
    sv = (squad_values
          .rename(columns={"team": team_col, "squad_value": value_col})
          .sort_values("date")
          .reset_index(drop=True))
    return pd.merge_asof(
        matches,
        sv,
        on="date",
        by=team_col,
        direction="backward",
    )

matches = add_squad_value(matches, squad_values, "home_team", "home_squad_value")
matches = add_squad_value(matches, squad_values, "away_team", "away_squad_value")

# ── 6. Diagnostics ────────────────────────────────────────────────────────────
total = len(matches)
matches["year"] = matches["date"].dt.year
matches["decade"] = (matches["year"] // 10 * 10).astype(str) + "s"

print("\n── Null coverage by decade ───────────────────────────────────────────")
decade_stats = matches.groupby("decade").agg(
    total=("home_squad_value", "count"),
    home_null=("home_squad_value", lambda x: x.isna().sum()),
    away_null=("away_squad_value", lambda x: x.isna().sum()),
).reset_index()
decade_stats["home_null_pct"] = (decade_stats["home_null"] / decade_stats["total"] * 100).round(1)
decade_stats["away_null_pct"] = (decade_stats["away_null"] / decade_stats["total"] * 100).round(1)
print(decade_stats.to_string(index=False))

print("\n── Null coverage by confederation (post-2004 only) ──────────────────")
# Map team to confederation via national_teams.csv
nt = pd.read_csv(RAW / "transfermarkt" / "national_teams.csv",
                 usecols=["country_name", "confederation"])
nt["team"] = nt["country_name"].map(canon)
team_to_conf = dict(zip(nt["team"], nt["confederation"]))

post2004 = matches[matches["year"] >= 2004].copy()
post2004["home_conf"] = post2004["home_team"].map(team_to_conf)
post2004["away_conf"] = post2004["away_team"].map(team_to_conf)

conf_nulls = []
for conf in sorted(post2004["home_conf"].dropna().unique()):
    sub = post2004[post2004["home_conf"] == conf]
    null_pct = sub["home_squad_value"].isna().mean() * 100
    conf_nulls.append({"confederation": conf, "matches": len(sub), "null_pct": round(null_pct, 1)})
print(pd.DataFrame(conf_nulls).to_string(index=False))

print("\n── Top 10 squad values (June 2026 snapshot) ─────────────────────────")
# Get most recent squad value per team
latest = (
    squad_values[squad_values["date"] <= pd.Timestamp("2026-06-09")]
    .sort_values("date")
    .groupby("team")
    .last()
    .reset_index()
    .sort_values("squad_value", ascending=False)
    .head(10)
    .reset_index(drop=True)
)
latest.index += 1
latest["squad_value_m"] = (latest["squad_value"] / 1e6).round(1)
print(latest[["team", "squad_value_m", "date"]].rename(
    columns={"squad_value_m": "value_EUR_M", "date": "as_of"}
).to_string())

expected = {"France", "England", "Spain", "Brazil", "Portugal", "Germany"}
actual = set(latest["team"])
missing = expected - actual
if missing:
    print(f"\nWARNING: expected top-10 teams missing: {missing}")
    for team in missing:
        row = (squad_values[squad_values["team"] == team]
               .sort_values("date").iloc[-1] if not squad_values[squad_values["team"] == team].empty else None)
        if row is not None:
            rank_in_all = (squad_values.groupby("team").last()
                           .sort_values("squad_value", ascending=False)
                           .index.tolist().index(team) + 1)
            print(f"  {team}: actual rank {rank_in_all}, value €{row['squad_value']/1e6:.1f}M")
else:
    print("\n✓ France, England, Spain, Brazil, Portugal, Germany all in top 10")

# Overall null summary
home_null = matches["home_squad_value"].isna().sum()
away_null = matches["away_squad_value"].isna().sum()
print(f"\n── Overall nulls ─────────────────────────────────────────────────────")
print(f"  home_squad_value: {home_null:,} / {total:,}  ({home_null/total:.1%})")
print(f"  away_squad_value: {away_null:,} / {total:,}  ({away_null/total:.1%})")

# ── 7. Save ───────────────────────────────────────────────────────────────────
matches = matches.drop(columns=["year", "decade"])
out_path = PROCESSED / "matches_with_elo_rank_value.parquet"
matches.to_parquet(out_path, index=False)
print(f"\nSaved → {out_path}")
print(f"Shape: {matches.shape}")
print(f"Columns: {list(matches.columns)}")
