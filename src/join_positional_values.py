"""
Phase 1d extension: Positional squad value features.

For each match adds 8 positional value columns (home/away × GK/DEF/MID/ATK)
and 2 tactical matchup differentials, using the same event-driven valuation
approach as join_market_values.py.

Positional pools (top-N by value, then mean):
  GK  → top 3   (1 starter + 2 cover)
  DEF → top 8   (4 starters + 4 cover)
  MID → top 8   (4 starters + 4 cover)
  ATK → top 6   (3 starters + 3 cover)

Matchup features:
  def_vs_atk_matchup = home_def_value - away_atk_value
  atk_vs_def_matchup = home_atk_value - away_def_value

All values in EUR. Leakage guard: all merge_asof use direction='backward'.
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

POS_TOP_N = {
    "Goalkeeper": 3,
    "Defender":   8,
    "Midfield":   8,
    "Attack":     6,
}
POS_FEATURE = {
    "Goalkeeper": "gk_value",
    "Defender":   "def_value",
    "Midfield":   "mid_value",
    "Attack":     "atk_value",
}

# ── 1. Canonical name map ─────────────────────────────────────────────────────
name_map = pd.read_csv(PROCESSED / "team_name_map.csv")
alias_to_canonical = dict(zip(name_map["alias"], name_map["canonical"]))


def canon(name: str) -> str:
    return alias_to_canonical.get(name, name)


# ── 2. Load players ───────────────────────────────────────────────────────────
players = pd.read_csv(
    RAW / "transfermarkt" / "players.csv",
    usecols=["player_id", "country_of_citizenship", "position"],
)
players["citizenship"] = players["country_of_citizenship"].map(canon)
players = players[
    players["citizenship"].notna() &
    players["position"].isin(POS_TOP_N)
].copy()

pid_to_cit = dict(zip(players["player_id"], players["citizenship"]))
pid_to_pos = dict(zip(players["player_id"], players["position"]))

# (citizenship, position) → set of player_ids
cit_pos_pids: dict[tuple, set] = defaultdict(set)
for pid, cit, pos in zip(players["player_id"], players["citizenship"], players["position"]):
    cit_pos_pids[(cit, pos)].add(pid)

print(f"Players loaded: {len(players):,}  "
      f"(excl. Missing position)")
print("Position breakdown:", players["position"].value_counts().to_dict())

# ── 3. Load valuations ────────────────────────────────────────────────────────
vals = pd.read_csv(
    RAW / "transfermarkt" / "player_valuations.csv",
    usecols=["player_id", "date", "market_value_in_eur"],
    parse_dates=["date"],
)
vals = vals[vals["player_id"].isin(pid_to_cit)].sort_values("date").reset_index(drop=True)
print(f"Valuations: {len(vals):,}  "
      f"({vals['date'].min().date()} – {vals['date'].max().date()})")

# ── 4. Event-driven positional value computation ──────────────────────────────
current_values: dict[int, float] = {}
positional_records: list[dict] = []

for val_date, batch in vals.groupby("date", sort=True):
    affected: set[tuple] = set()

    for row in batch.itertuples(index=False):
        pid = row.player_id
        current_values[pid] = row.market_value_in_eur
        cit = pid_to_cit.get(pid)
        pos = pid_to_pos.get(pid)
        if cit and pos:
            affected.add((cit, pos))

    for (cit, pos) in affected:
        values = [current_values[p] for p in cit_pos_pids[(cit, pos)]
                  if p in current_values]
        if not values:
            continue
        n = POS_TOP_N[pos]
        top_n = sorted(values, reverse=True)[:n]
        positional_records.append({
            "team":     cit,
            "position": pos,
            "date":     val_date,
            "value":    float(np.mean(top_n)),
        })

pos_df = pd.DataFrame(positional_records)
print(f"\nPositional snapshots: {len(pos_df):,}  "
      f"({pos_df['team'].nunique()} teams, "
      f"{pos_df['date'].nunique()} unique dates)")
print("Records per position:")
print(pos_df["position"].value_counts().to_string())

# ── 5. Load matches and merge_asof for each position × side ──────────────────
matches = pd.read_parquet(PROCESSED / "matches_with_elo_rank_value.parquet")
matches = matches.sort_values("date").reset_index(drop=True)
print(f"\nMatches loaded: {len(matches):,}")

for pos, feat in POS_FEATURE.items():
    lookup = (pos_df[pos_df["position"] == pos]
              .drop(columns="position")
              .rename(columns={"value": feat})
              .sort_values("date")
              .reset_index(drop=True))

    # Home side
    matches = pd.merge_asof(
        matches,
        lookup.rename(columns={"team": "home_team", feat: f"home_{feat}"}),
        on="date", by="home_team", direction="backward",
    )
    # Away side
    matches = pd.merge_asof(
        matches,
        lookup.rename(columns={"team": "away_team", feat: f"away_{feat}"}),
        on="date", by="away_team", direction="backward",
    )

# ── 6. Matchup differential features ─────────────────────────────────────────
matches["def_vs_atk_matchup"] = matches["home_def_value"] - matches["away_atk_value"]
matches["atk_vs_def_matchup"] = matches["home_atk_value"] - matches["away_def_value"]

# ── 7. Diagnostics ────────────────────────────────────────────────────────────
pos_cols = [f"{side}_{feat}"
            for side in ("home", "away")
            for feat in POS_FEATURE.values()]

print("\n── Null coverage by decade ───────────────────────────────────────────")
matches["decade"] = (matches["date"].dt.year // 10 * 10).astype(str) + "s"
for col in pos_cols:
    null_by_dec = matches.groupby("decade")[col].apply(lambda x: f"{x.isna().mean():.0%}")
    print(f"  {col:25s}: " + "  ".join(f"{d}={v}" for d, v in null_by_dec.items()))

print("\n── Top 5 teams by atk_value (June 2026 snapshot) ────────────────────")
latest_date = pd.Timestamp("2026-06-09")
latest_atk = (
    pos_df[(pos_df["position"] == "Attack") & (pos_df["date"] <= latest_date)]
    .sort_values("date")
    .groupby("team").last()
    .reset_index()
    .sort_values("value", ascending=False)
    .head(5)
    .reset_index(drop=True)
)
latest_atk.index += 1
latest_atk["value_M"] = (latest_atk["value"] / 1e6).round(1)
print(latest_atk[["team", "value_M"]].rename(columns={"value_M": "mean_top6_ATK_EUR_M"}).to_string())

print("\n── Top 5 teams by gk_value (June 2026 snapshot) ─────────────────────")
latest_gk = (
    pos_df[(pos_df["position"] == "Goalkeeper") & (pos_df["date"] <= latest_date)]
    .sort_values("date")
    .groupby("team").last()
    .reset_index()
    .sort_values("value", ascending=False)
    .head(5)
    .reset_index(drop=True)
)
latest_gk.index += 1
latest_gk["value_M"] = (latest_gk["value"] / 1e6).round(1)
print(latest_gk[["team", "value_M"]].rename(columns={"value_M": "mean_top3_GK_EUR_M"}).to_string())

print("\n── Matchup feature distributions ────────────────────────────────────")
for col in ("def_vs_atk_matchup", "atk_vs_def_matchup"):
    s = matches[col].dropna()
    print(f"  {col}: mean={s.mean()/1e6:+.1f}M  "
          f"std={s.std()/1e6:.1f}M  "
          f"min={s.min()/1e6:.1f}M  max={s.max()/1e6:.1f}M  "
          f"nulls={matches[col].isna().sum():,}")

print("\n── Spot-check: 2022 WC Final (Argentina vs France) ──────────────────")
final = matches[
    (matches["date"].dt.strftime("%Y-%m-%d") == "2022-12-18") &
    (matches["home_team"] == "Argentina") &
    (matches["away_team"] == "France")
]
if not final.empty:
    r = final.iloc[0]
    for side in ("home", "away"):
        team = r[f"{side}_team"]
        gk  = r[f"{side}_gk_value"]
        dfv = r[f"{side}_def_value"]
        mid = r[f"{side}_mid_value"]
        atk = r[f"{side}_atk_value"]
        print(f"  {team:12s}  GK={gk/1e6:.1f}M  DEF={dfv/1e6:.1f}M  "
              f"MID={mid/1e6:.1f}M  ATK={atk/1e6:.1f}M")
    print(f"  def_vs_atk={r['def_vs_atk_matchup']/1e6:+.1f}M  "
          f"atk_vs_def={r['atk_vs_def_matchup']/1e6:+.1f}M")
else:
    print("  NOT FOUND")

print("\n── Overall null counts ───────────────────────────────────────────────")
for col in pos_cols + ["def_vs_atk_matchup", "atk_vs_def_matchup"]:
    n = matches[col].isna().sum()
    print(f"  {col:30s}: {n:,}  ({n/len(matches):.1%})")

# ── 8. Save ───────────────────────────────────────────────────────────────────
matches = matches.drop(columns=["decade"])
out_path = PROCESSED / "matches_with_elo_rank_value_positional.parquet"
matches.to_parquet(out_path, index=False)
print(f"\nSaved → {out_path}")
print(f"Shape: {matches.shape}")
print(f"Columns: {list(matches.columns)}")
