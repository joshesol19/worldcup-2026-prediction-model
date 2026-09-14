"""
Phase 1e: Walk-forward sliding-window form features.

Unfold matches into a per-team log, compute rolling features using only
prior matches, then fold back into match-level home/away columns.

Count-based windows (last N matches):
  last10_pts, last10_gd, last10_avg_opp_elo, last10_elo_delta
  last5_pts, last5_gd
  last10_pts_weighted, last10_gd_weighted

Time-based windows (calendar days, closed='left' excludes current match):
  last180d_pts_per_match, last180d_gd_per_match
  last365d_matches_played, last365d_pts_per_match

Leakage guard:
  Count-based: shift(1) before rolling — current match never enters its own window.
  Time-based:  rolling(offset, closed='left') — window is [t-N_days, t_match).
"""

import pandas as pd
import numpy as np
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

# ── 1. Load input ─────────────────────────────────────────────────────────────
df = pd.read_parquet(PROCESSED / "matches_with_elo_rank_value_positional.parquet")
df = df.sort_values("date").reset_index(drop=True)
print(f"Input: {len(df):,} rows  ({df['date'].min().date()} – {df['date'].max().date()})")

# ── 2. Build per-team match log ───────────────────────────────────────────────
comp_weight = {1: 1.0, 2: 1.0, 3: 1.0, 4: 0.3, 5: 0.3}

home = df[["date", "home_team", "away_team", "home_score", "away_score",
           "home_elo_pre", "away_elo_pre", "competition_tier", "outcome"]].copy()
home = home.rename(columns={
    "home_team": "team", "away_team": "opponent",
    "home_elo_pre": "team_elo_pre", "away_elo_pre": "opp_elo",
})
home["pts"] = home["outcome"].map({"H": 3, "D": 1, "A": 0})
home["gd"]  = home["home_score"] - home["away_score"]

away = df[["date", "away_team", "home_team", "home_score", "away_score",
           "away_elo_pre", "home_elo_pre", "competition_tier", "outcome"]].copy()
away = away.rename(columns={
    "away_team": "team", "home_team": "opponent",
    "away_elo_pre": "team_elo_pre", "home_elo_pre": "opp_elo",
})
away["pts"] = away["outcome"].map({"H": 0, "D": 1, "A": 3})
away["gd"]  = away["away_score"] - away["home_score"]

log = (pd.concat([home, away], ignore_index=True)
       .sort_values(["team", "date"])
       .reset_index(drop=True))

log["weight"] = log["competition_tier"].map(comp_weight)
log["pts_w"]  = log["pts"] * log["weight"]
log["gd_w"]   = log["gd"]  * log["weight"]

print(f"Team log built: {len(log):,} rows  ({log['team'].nunique()} teams)")

# ── 3a. Count-based features — shift(1) within group, then rolling ────────────
g = log.groupby("team", sort=False)

# Shift each series within its team group
for src, dst in [("pts", "pts_s"), ("gd", "gd_s"), ("opp_elo", "opp_elo_s"),
                 ("pts_w", "pts_w_s"), ("gd_w", "gd_w_s")]:
    log[dst] = g[src].shift(1)

# Elo 10 matches ago (for delta)
log["elo_10ago"] = g["team_elo_pre"].shift(10)

# Rolling over the shifted columns
for col, window, agg, out in [
    ("pts_s",     10, "sum",  "last10_pts"),
    ("gd_s",      10, "sum",  "last10_gd"),
    ("opp_elo_s", 10, "mean", "last10_avg_opp_elo"),
    ("pts_s",      5, "sum",  "last5_pts"),
    ("gd_s",       5, "sum",  "last5_gd"),
    ("pts_w_s",   10, "sum",  "last10_pts_weighted"),
    ("gd_w_s",    10, "sum",  "last10_gd_weighted"),
]:
    log[out] = g[col].transform(
        lambda x, w=window, a=agg: getattr(x.rolling(w, min_periods=1), a)()
    )

log["last10_elo_delta"] = log["team_elo_pre"] - log["elo_10ago"]

# ── 3b. Time-based features — rolling offset with closed='left' ───────────────
def _time_features(grp: pd.DataFrame) -> pd.DataFrame:
    grp = grp.sort_values("date").copy()
    idx = grp.set_index("date")  # DatetimeIndex required for offset rolling

    r180 = idx.rolling("180D", closed="left")
    r365 = idx.rolling("365D", closed="left")

    grp["last180d_pts_per_match"]   = r180["pts"].mean().values
    grp["last180d_gd_per_match"]    = r180["gd"].mean().values
    grp["last365d_matches_played"]  = r365["pts"].count().values
    grp["last365d_pts_per_match"]   = r365["pts"].mean().values

    return grp

print("Computing time-based rolling features…")
log = log.groupby("team", group_keys=False).apply(_time_features)
log = log.sort_values(["team", "date"]).reset_index(drop=True)

FORM_COLS = [
    "last10_pts", "last10_gd", "last10_avg_opp_elo", "last10_elo_delta",
    "last5_pts", "last5_gd",
    "last10_pts_weighted", "last10_gd_weighted",
    "last180d_pts_per_match", "last180d_gd_per_match",
    "last365d_matches_played", "last365d_pts_per_match",
]

# ── 4. Leakage verification ───────────────────────────────────────────────────
print("\n── Leakage verification (5 random matches) ──────────────────────────")
# Pick matches with enough history (post-2005, team has at least 10 prior matches)
candidates = df[(df["date"].dt.year >= 2005)].sample(5, random_state=42)

for _, row in candidates.iterrows():
    team    = row["home_team"]
    mdate   = row["date"]

    # Computed feature value
    team_row = log[(log["team"] == team) & (log["date"] == mdate)]
    if team_row.empty:
        print(f"  {team} {mdate.date()}: not found in log")
        continue
    computed = team_row["last10_pts"].iloc[0]

    # Manual calculation: 10 matches strictly before this date for this team
    prior = log[(log["team"] == team) & (log["date"] < mdate)].tail(10)
    manual = prior["pts"].sum() if len(prior) > 0 else np.nan

    match_str = f"{row['home_team']} vs {row['away_team']}"
    ok = "✓" if np.isclose(computed, manual, equal_nan=True) else "✗ MISMATCH"
    print(f"  {ok} {mdate.date()} {match_str:35s}  "
          f"computed={computed:.0f}  manual={manual:.0f}  "
          f"prior_matches={len(prior)}")

# Early-career check
print("\n── Early-career partial-window check ────────────────────────────────")
all_teams = log["team"].unique()
sample_team = random.choice(all_teams)
first5 = log[log["team"] == sample_team].head(5)[
    ["date", "team", "pts", "last10_pts", "last5_pts", "last10_elo_delta"]
]
print(f"  First 5 matches for '{sample_team}':")
print(first5.to_string(index=False))
print("  (last10_pts uses available prior matches; last10_elo_delta NaN until 10th match)")

# ── 5. Join form features back to matches ─────────────────────────────────────
lookup = log[["team", "date"] + FORM_COLS].drop_duplicates(subset=["team", "date"])

# Home
home_lookup = lookup.rename(columns={"team": "home_team",
                                     **{c: f"home_{c}" for c in FORM_COLS}})
df = df.merge(home_lookup, on=["home_team", "date"], how="left")

# Away
away_lookup = lookup.rename(columns={"team": "away_team",
                                     **{c: f"away_{c}" for c in FORM_COLS}})
df = df.merge(away_lookup, on=["away_team", "date"], how="left")

# ── 6. Diagnostics ────────────────────────────────────────────────────────────
print("\n── Null rates by decade ──────────────────────────────────────────────")
df["decade"] = (df["date"].dt.year // 10 * 10).astype(str) + "s"
home_form_cols = [f"home_{c}" for c in FORM_COLS]
# Print a compact summary (one row per feature, null% by decade)
decade_order = sorted(df["decade"].unique())
for col in home_form_cols:
    parts = []
    for dec in decade_order:
        pct = df[df["decade"] == dec][col].isna().mean()
        parts.append(f"{dec}={pct:.0%}")
    print(f"  {col:35s}: " + "  ".join(parts))

print("\n── last10_pts distribution (home team) ──────────────────────────────")
s = df["home_last10_pts"].dropna()
print(f"  mean={s.mean():.1f}  std={s.std():.1f}  "
      f"min={s.min():.0f}  max={s.max():.0f}")
buckets = pd.cut(s, bins=range(0, 32, 3), right=False)
print(f"  {buckets.value_counts().sort_index().to_string()}")

print("\n── Top 10 by last365d_pts_per_match (as of June 2026) ───────────────")
latest_date = pd.Timestamp("2026-06-09")
top_form = (
    log[log["date"] <= latest_date]
    .sort_values("date")
    .groupby("team")[["last365d_pts_per_match", "last365d_matches_played"]]
    .last()
    .reset_index()
    .dropna(subset=["last365d_pts_per_match"])
    .query("last365d_matches_played >= 5")   # require at least 5 matches
    .sort_values("last365d_pts_per_match", ascending=False)
    .head(10)
    .reset_index(drop=True)
)
top_form.index += 1
top_form["last365d_pts_per_match"] = top_form["last365d_pts_per_match"].round(2)
top_form["last365d_matches_played"] = top_form["last365d_matches_played"].astype(int)
print(top_form.to_string())

print("\n── Brazil 2022 WC QF (vs Croatia, 2022-12-09) ───────────────────────")
print("  NOTE: Brazil was eliminated in QF — they did not reach the Final.")
bra_qf = df[
    (df["date"].dt.strftime("%Y-%m-%d") == "2022-12-09") &
    (df["away_team"] == "Brazil")  # Brazil was away vs Croatia
]
if not bra_qf.empty:
    r = bra_qf.iloc[0]
    print(f"  Match: {r['home_team']} vs {r['away_team']}  "
          f"({r['home_score']:.0f}–{r['away_score']:.0f}, {r['outcome']})")
    print(f"  Brazil (away) last10_pts       = {r['away_last10_pts']:.0f}  "
          f"(max possible = 30)")
    print(f"  Brazil (away) last5_pts        = {r['away_last5_pts']:.0f}")
    print(f"  Brazil (away) last10_elo_delta = {r['away_last10_elo_delta']:.1f}")
    print(f"  Brazil (away) last365d_pts/m   = {r['away_last365d_pts_per_match']:.2f}")
    # Cross-check: show the 10 prior matches manually
    prior10 = log[(log["team"] == "Brazil") & (log["date"] < pd.Timestamp("2022-12-09"))].tail(10)
    print(f"\n  10 matches before QF (Brazil perspective):")
    print(prior10[["date", "opponent", "pts", "gd", "competition_tier"]].to_string(index=False))
    print(f"  Manual sum pts = {prior10['pts'].sum():.0f}")
else:
    print("  Brazil QF match not found — check team name or date")

# ── 7. Save ───────────────────────────────────────────────────────────────────
df = df.drop(columns=["decade"])
out_path = PROCESSED / "master_matches.parquet"
df.to_parquet(out_path, index=False)
print(f"\nSaved → {out_path}")
print(f"Shape: {df.shape}")
print(f"Columns ({len(df.columns)}): {list(df.columns)}")
