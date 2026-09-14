"""
Phase 1b: Derive match_stage, competition_tier, and walk-forward Elo.

Elo is computed from full Jurisoo history (1872+) so teams entering the
1990+ training window carry realistic ratings rather than the cold-start 1500.
Output is filtered to 1990+ with scored matches only.
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# ── 1. Team name canonical map ────────────────────────────────────────────────
name_map = pd.read_csv(PROCESSED / "team_name_map.csv")
alias_to_canonical = dict(zip(name_map["alias"], name_map["canonical"]))


def canon(name: str) -> str:
    return alias_to_canonical.get(name, name)


# ── 2. Load full Jurisoo history ──────────────────────────────────────────────
df = pd.read_csv(RAW / "jurisoo" / "results.csv", parse_dates=["date"])
df["home_team"] = df["home_team"].map(canon)
df["away_team"] = df["away_team"].map(canon)
df = df.sort_values("date").reset_index(drop=True)
print(f"Full Jurisoo: {len(df):,} matches  ({df['date'].min().date()} – {df['date'].max().date()})")

# ── 3. Build Fjelstul WC-stage lookup ─────────────────────────────────────────
fj = pd.read_csv(RAW / "fjelstul" / "data-csv" / "matches.csv", parse_dates=["match_date"])
fj["home_team_name"] = fj["home_team_name"].map(canon)
fj["away_team_name"] = fj["away_team_name"].map(canon)

_FJELSTUL_STAGE = {
    "group stage": "wc_group",
    "second group stage": "wc_group",   # 1974/1982 second-round group format
    "final round": "wc_group",           # 1974 final group round
    "round of 16": "wc_r16",
    "quarter-finals": "wc_qf",
    "quarter-final": "wc_qf",
    "semi-finals": "wc_sf",
    "semi-final": "wc_sf",
    "third-place match": "wc_3rd",
    "final": "wc_final",
}
fj["wc_stage"] = fj["stage_name"].map(_FJELSTUL_STAGE)

# Primary key: (date, home_canonical, away_canonical)
fj_lookup: dict[tuple, str] = {}
for _, row in fj.iterrows():
    key = (row["match_date"].date(), row["home_team_name"], row["away_team_name"])
    fj_lookup[key] = row["wc_stage"]

# ── 4. Classify tournaments ───────────────────────────────────────────────────
# Tournaments that map to 'friendly' but are non-FIFA / regional minor events
# → competition_tier 5 (lower Elo K-weight than standard friendlies)
_MINOR_TOURNAMENTS = {
    "Viva World Cup",
    "CONIFA World Football Cup",
    "CONIFA European Football Cup",
    "Island Games",
    "Southeast Asian Games",
    "Asian Games",
    "South Asian Games",
    "Pacific Games",
    "South Pacific Games",
    "South Pacific Mini Games",
    "Pacific Mini Games",
    "Indian Ocean Island Games",
    "Inter Games",
    "MSG Prime Minister's Cup",
    "East Asian Games",
}

# Substrings that mark a continental championship (not qualification)
_CONTINENTAL_KEYWORDS = [
    "UEFA Euro",
    "Copa América",
    "Copa America",
    "African Cup of Nations",
    "AFC Asian Cup",
    "Gold Cup",
    "Oceania Nations Cup",
    "Confederations Cup",
    "UEFA Nations League",
    "CONCACAF Nations League",
    "AFF Championship",
    "EAFF Championship",
    "WAFF Championship",
    "Gulf Cup",
    "COSAFA Cup",
    "CECAFA Cup",
    "SAFF Cup",
    "UNCAF Cup",
    "Arab Cup",
    "Amílcar Cabral Cup",
    "CFU Caribbean Cup",
]

WC_KNOCKOUT_STAGES = {"wc_r32", "wc_r16", "wc_qf", "wc_sf", "wc_3rd", "wc_final"}


def _classify(row) -> tuple[str, int]:
    """Return (match_stage, competition_tier)."""
    t: str = row["tournament"]
    t_lower = t.lower()

    # World Cup proper — look up actual stage in Fjelstul
    if t == "FIFA World Cup":
        date_key = row["date"].date()
        stage = fj_lookup.get((date_key, row["home_team"], row["away_team"]))
        if stage is None:
            # Try swapped order as a safety fallback
            stage = fj_lookup.get((date_key, row["away_team"], row["home_team"]))
        if stage is None:
            # 2026 matches not in Fjelstul yet; null score rows are dropped
            # later, so this only affects unscored fixtures — label conservatively
            stage = "wc_group"
        tier = 1 if stage in WC_KNOCKOUT_STAGES else 2
        return stage, tier

    # Any qualification tournament (WC qual, Euro qual, AFCON qual, etc.)
    if "qualification" in t_lower or "qualifier" in t_lower:
        return "qualification_wc", 3

    # Continental championships
    if any(kw in t for kw in _CONTINENTAL_KEYWORDS):
        return "continental_group", 2

    # Non-FIFA / minor regional events
    if t in _MINOR_TOURNAMENTS:
        return "friendly", 5

    # Everything else: standard friendly
    return "friendly", 4


print("Classifying tournaments…")
results = df.apply(_classify, axis=1)
df["match_stage"] = [r[0] for r in results]
df["competition_tier"] = [r[1] for r in results]

# ── 5. Walk-forward Elo (over full history, including pre-1990) ───────────────
# K-factor per match_stage; minor friendlies (tier 5) use K=5
_ELO_K: dict[str, float] = {
    "wc_group": 60.0,
    "wc_r32": 60.0,
    "wc_r16": 60.0,
    "wc_qf": 60.0,
    "wc_sf": 60.0,
    "wc_3rd": 60.0,
    "wc_final": 60.0,
    "continental_group": 40.0,
    "qualification_wc": 25.0,
    "friendly": 10.0,   # tier 4 and 5 both get 10; tier-5 flag handles model weight
}

print("Computing walk-forward Elo…")
elo: dict[str, float] = {}
home_elo_pre: list[float] = []
away_elo_pre: list[float] = []

for _, row in df.iterrows():
    h, a = row["home_team"], row["away_team"]
    h_elo = elo.get(h, 1500.0)
    a_elo = elo.get(a, 1500.0)

    home_elo_pre.append(h_elo)
    away_elo_pre.append(a_elo)

    # Only update ratings when the match has a result
    if pd.notna(row["home_score"]) and pd.notna(row["away_score"]):
        hs, as_ = float(row["home_score"]), float(row["away_score"])
        actual = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        expected = 1.0 / (1.0 + 10.0 ** ((a_elo - h_elo) / 400.0))
        k = _ELO_K.get(row["match_stage"], 10.0)
        delta = k * (actual - expected)
        elo[h] = h_elo + delta
        elo[a] = a_elo - delta

df["home_elo_pre"] = home_elo_pre
df["away_elo_pre"] = away_elo_pre

# ── 6. Filter to 1990+, drop unscored rows ────────────────────────────────────
df_1990 = df[df["date"] >= "1990-01-01"].copy()
print(f"\nAfter 1990+ filter:    {len(df_1990):,} matches")

df_out = df_1990.dropna(subset=["home_score", "away_score"]).reset_index(drop=True)
print(f"After null-score drop: {len(df_out):,} matches  "
      f"(dropped {len(df_1990) - len(df_out):,} unscored fixtures)")

# ── 7. Add outcome column ─────────────────────────────────────────────────────
df_out["outcome"] = np.where(
    df_out["home_score"] > df_out["away_score"], "H",
    np.where(df_out["home_score"] == df_out["away_score"], "D", "A"),
)

# ── 8. Save ───────────────────────────────────────────────────────────────────
out_path = PROCESSED / "matches_with_elo.parquet"
df_out.to_parquet(out_path, index=False)
print(f"\nSaved → {out_path}")
print(f"Shape: {df_out.shape}")
print(f"Columns: {list(df_out.columns)}")

# ── 9. Sanity checks ──────────────────────────────────────────────────────────
print("\n── match_stage distribution ──────────────────────────────────────────")
print(df_out["match_stage"].value_counts().to_string())

print("\n── competition_tier distribution ─────────────────────────────────────")
print(df_out["competition_tier"].value_counts().sort_index().to_string())

print("\n── outcome distribution ──────────────────────────────────────────────")
vc = df_out["outcome"].value_counts()
total = len(df_out)
for label, count in vc.items():
    print(f"  {label}: {count:,}  ({count/total:.1%})")

print("\n── Top 10 teams by current Elo ───────────────────────────────────────")
top10 = (
    pd.DataFrame({"team": list(elo.keys()), "elo": list(elo.values())})
    .sort_values("elo", ascending=False)
    .head(10)
    .reset_index(drop=True)
)
top10.index += 1
print(top10.to_string())

expected_top5 = {"Brazil", "Germany", "France", "Argentina", "Spain"}
actual_top10 = set(top10["team"])
missing = expected_top5 - actual_top10
if missing:
    print(f"\nWARNING: expected top-5 teams absent from top 10: {missing}")
    # Show where they actually rank
    all_teams = (
        pd.DataFrame({"team": list(elo.keys()), "elo": list(elo.values())})
        .sort_values("elo", ascending=False)
        .reset_index(drop=True)
    )
    for team in missing:
        rank = all_teams[all_teams["team"] == team].index[0] + 1
        e = all_teams.loc[rank - 1, "elo"]
        print(f"  {team}: rank {rank}, Elo {e:.1f}")
else:
    print("\n✓ Brazil, Germany, France, Argentina, Spain all in top 10")

# Elo range sanity check
all_elos = list(elo.values())
print(f"\nElo range across {len(all_elos)} tracked teams: "
      f"{min(all_elos):.1f} – {max(all_elos):.1f}  "
      f"(mean {np.mean(all_elos):.1f})")
