"""
Inference script for World Cup 2026/2022 match predictions.
Called by the .NET backend at startup to generate predictions_2026.json
and predictions_2022.json into backend/cache/.

Usage: python inference.py
"""
import os
import sys
import json
import logging
import difflib
import warnings
import numpy as np
import pandas as pd
import joblib

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CACHE_DIR = os.path.join(SCRIPT_DIR, "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Feature name → plain English labels
# ---------------------------------------------------------------------------
FEATURE_LABELS = {
    "home_elo_pre":              "Elo rating",
    "away_elo_pre":              "Elo rating",
    "elo_diff":                  "Elo rating",
    "home_fifa_rank":            "FIFA ranking",
    "away_fifa_rank":            "FIFA ranking",
    "neutral":                   "Neutral venue",
    "competition_tier":          "Match stakes",
    "home_last10_pts":           "Recent form (last 10)",
    "home_last10_gd":            "Recent goal difference",
    "home_last10_avg_opp_elo":   "Strength of schedule",
    "home_last10_elo_delta":     "Elo trajectory",
    "home_last5_pts":            "Recent form (last 5)",
    "home_last5_gd":             "Recent goal difference",
    "home_last10_pts_weighted":  "Weighted recent form",
    "home_last10_gd_weighted":   "Weighted goal difference",
    "away_last10_pts":           "Recent form (last 10)",
    "away_last10_gd":            "Recent goal difference",
    "away_last10_avg_opp_elo":   "Strength of schedule",
    "away_last10_elo_delta":     "Elo trajectory",
    "away_last5_pts":            "Recent form (last 5)",
    "away_last5_gd":             "Recent goal difference",
    "away_last10_pts_weighted":  "Weighted recent form",
    "away_last10_gd_weighted":   "Weighted goal difference",
    "home_last180d_pts_per_match": "Form (last 6 months)",
    "home_last180d_gd_per_match":  "Goal diff (last 6 months)",
    "home_last365d_matches_played":"Matches played (past year)",
    "home_last365d_pts_per_match": "Form (past year)",
    "away_last180d_pts_per_match": "Form (last 6 months)",
    "away_last180d_gd_per_match":  "Goal diff (last 6 months)",
    "away_last365d_matches_played":"Matches played (past year)",
    "away_last365d_pts_per_match": "Form (past year)",
    "home_squad_value":          "Squad market value",
    "away_squad_value":          "Squad market value",
    "home_gk_value":             "Goalkeeper value",
    "away_gk_value":             "Goalkeeper value",
    "home_def_value":            "Defensive value",
    "away_def_value":            "Defensive value",
    "home_mid_value":            "Midfield value",
    "away_mid_value":            "Midfield value",
    "home_atk_value":            "Attacking value",
    "away_atk_value":            "Attacking value",
    "def_vs_atk_matchup":        "Defense vs attack matchup",
    "atk_vs_def_matchup":        "Attack vs defense matchup",
}

# ---------------------------------------------------------------------------
# Flag emoji map (openfootball canonical names → emoji)
# ---------------------------------------------------------------------------
FLAGS = {
    "Mexico": "🇲🇽", "South Africa": "🇿🇦", "South Korea": "🇰🇷",
    "Czech Republic": "🇨🇿", "Canada": "🇨🇦", "Bosnia & Herzegovina": "🇧🇦",
    "Bosnia and Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "Switzerland": "🇨🇭",
    "United States": "🇺🇸", "USA": "🇺🇸", "Panama": "🇵🇦",
    "Honduras": "🇭🇳", "Argentina": "🇦🇷", "Chile": "🇨🇱",
    "Ecuador": "🇪🇨", "Peru": "🇵🇪", "Colombia": "🇨🇴",
    "Uruguay": "🇺🇾", "Brazil": "🇧🇷", "Paraguay": "🇵🇾",
    "Venezuela": "🇻🇪", "Bolivia": "🇧🇴", "Germany": "🇩🇪",
    "France": "🇫🇷", "Spain": "🇪🇸", "Portugal": "🇵🇹",
    "England": "󠁧󠁢󠁥󠁮󠁧󠁿", "Netherlands": "🇳🇱", "Belgium": "🇧🇪",
    "Italy": "🇮🇹", "Croatia": "🇭🇷", "Denmark": "🇩🇰",
    "Austria": "🇦🇹", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Serbia": "🇷🇸",
    "Poland": "🇵🇱", "Hungary": "🇭🇺", "Slovakia": "🇸🇰",
    "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Romania": "🇷🇴", "Ukraine": "🇺🇦",
    "Turkey": "🇹🇷", "Norway": "🇳🇴", "Sweden": "🇸🇪",
    "Finland": "🇫🇮", "Greece": "🇬🇷", "Albania": "🇦🇱",
    "Georgia": "🇬🇪", "Slovenia": "🇸🇮", "Morocco": "🇲🇦",
    "Senegal": "🇸🇳", "Tunisia": "🇹🇳", "Cameroon": "🇨🇲",
    "Ghana": "🇬🇭", "Nigeria": "🇳🇬", "Egypt": "🇪🇬",
    "Algeria": "🇩🇿", "Ivory Coast": "🇨🇮", "Cote d'Ivoire": "🇨🇮",
    "Mali": "🇲🇱", "Congo DR": "🇨🇩", "DR Congo": "🇨🇩",
    "Tanzania": "🇹🇿", "Comoros": "🇰🇲", "Benin": "🇧🇯",
    "Zimbabwe": "🇿🇼", "Japan": "🇯🇵", "Australia": "🇦🇺",
    "Iran": "🇮🇷", "Saudi Arabia": "🇸🇦", "South Korea": "🇰🇷",
    "Uzbekistan": "🇺🇿", "Jordan": "🇯🇴", "Iraq": "🇮🇶",
    "Indonesia": "🇮🇩", "New Zealand": "🇳🇿", "China": "🇨🇳",
    "United Arab Emirates": "🇦🇪", "Bahrain": "🇧🇭", "Kuwait": "🇰🇼",
    "Venezuela": "🇻🇪", "Costa Rica": "🇨🇷", "El Salvador": "🇸🇻",
    "Jamaica": "🇯🇲", "Trinidad & Tobago": "🇹🇹",
    "Trinidad and Tobago": "🇹🇹",
    "Cape Verde": "🇨🇻", "Curaçao": "🇨🇼", "Haiti": "🇭🇹",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
}


def get_flag(name: str) -> str:
    return FLAGS.get(name, "🏳️")


# ---------------------------------------------------------------------------
# Load artifacts
# ---------------------------------------------------------------------------
def load_artifacts():
    log.info("Loading model artifacts...")
    model = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_model_final.joblib"))
    expl_model = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_model_explanatory.joblib"))
    le = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_label_encoder.joblib"))
    feat_cols = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_feature_cols.joblib"))
    log.info(f"Model loaded. Features: {len(feat_cols)}. Classes: {list(le.classes_)}")
    return model, expl_model, le, feat_cols


# ---------------------------------------------------------------------------
# Override fifa_rank in snapshots from the most recent scraped rankings file
# ---------------------------------------------------------------------------
def override_fifa_ranks(snapshots: dict, name_map: dict) -> None:
    """
    Reads the most recent file in scraped_data/ and overwrites snap["fifa_rank"]
    for every team that resolves to a canonical name. Operates in-place.
    The parquet only carries rankings up to Jan 19 2026 (newest match is Mar 31,
    merge_asof can't reach the Apr 1 snapshot). This fixes that without a rebuild.
    """
    import glob as _glob
    scraped_dir = os.path.join(DATA_DIR, "raw", "fifa_rankings", "scraped_data")
    files = _glob.glob(os.path.join(scraped_dir, "*.csv"))
    if not files:
        log.warning("No scraped ranking files found — skipping override")
        return

    all_canonicals = list(snapshots.keys())

    frames = []
    for f in files:
        try:
            frames.append(pd.read_csv(f, parse_dates=["date"]))
        except Exception:
            continue
    raw = pd.concat(frames, ignore_index=True)
    raw = raw.dropna(subset=["date"])
    latest_date = raw["date"].max()
    latest = raw[raw["date"] == latest_date].copy()

    updated = 0
    for _, row in latest.iterrows():
        country_raw = str(row["country"]).strip()
        canon = canonicalize(country_raw, name_map, all_canonicals)
        if canon and canon in snapshots:
            snapshots[canon]["fifa_rank"] = float(row["rank"])
            updated += 1

    log.info(f"FIFA rank override: {updated} teams updated from {str(latest_date)[:10]} snapshot")


# ---------------------------------------------------------------------------
# Team name canonicalization
# ---------------------------------------------------------------------------
def build_name_map():
    path = os.path.join(DATA_DIR, "processed", "team_name_map.csv")
    df = pd.read_csv(path)
    # alias → canonical
    mapping = dict(zip(df["alias"].str.strip(), df["canonical"].str.strip()))
    return mapping


def canonicalize(name: str, mapping: dict, all_canonicals: list) -> str | None:
    name = name.strip()
    if name in mapping:
        return mapping[name]
    # direct canonical hit
    if name in all_canonicals:
        return name
    # fuzzy fallback
    close = difflib.get_close_matches(name, list(mapping.keys()) + all_canonicals, n=1, cutoff=0.7)
    if close:
        matched = close[0]
        canon = mapping.get(matched, matched)
        log.warning(f"Fuzzy name match: '{name}' → '{matched}' → '{canon}'")
        return canon
    log.error(f"Could not canonicalize team name: '{name}'")
    return None


# ---------------------------------------------------------------------------
# Build per-team feature snapshot (most recent row in parquet)
# ---------------------------------------------------------------------------
TEAM_FEATURE_MAP = {
    "elo": ("home_elo_pre", "away_elo_pre"),
    "fifa_rank": ("home_fifa_rank", "away_fifa_rank"),
    "last10_pts": ("home_last10_pts", "away_last10_pts"),
    "last10_gd": ("home_last10_gd", "away_last10_gd"),
    "last10_avg_opp_elo": ("home_last10_avg_opp_elo", "away_last10_avg_opp_elo"),
    "last10_elo_delta": ("home_last10_elo_delta", "away_last10_elo_delta"),
    "last5_pts": ("home_last5_pts", "away_last5_pts"),
    "last5_gd": ("home_last5_gd", "away_last5_gd"),
    "last10_pts_weighted": ("home_last10_pts_weighted", "away_last10_pts_weighted"),
    "last10_gd_weighted": ("home_last10_gd_weighted", "away_last10_gd_weighted"),
    "last180d_pts_per_match": ("home_last180d_pts_per_match", "away_last180d_pts_per_match"),
    "last180d_gd_per_match": ("home_last180d_gd_per_match", "away_last180d_gd_per_match"),
    "last365d_matches_played": ("home_last365d_matches_played", "away_last365d_matches_played"),
    "last365d_pts_per_match": ("home_last365d_pts_per_match", "away_last365d_pts_per_match"),
    "squad_value": ("home_squad_value", "away_squad_value"),
    "gk_value": ("home_gk_value", "away_gk_value"),
    "def_value": ("home_def_value", "away_def_value"),
    "mid_value": ("home_mid_value", "away_mid_value"),
    "atk_value": ("home_atk_value", "away_atk_value"),
}


def build_team_snapshots(df: pd.DataFrame) -> dict:
    """For each canonical team name, extract stats from their most recent appearance."""
    snapshots = {}
    all_teams = set(df["home_team"].unique()) | set(df["away_team"].unique())

    for team in all_teams:
        home_rows = df[df["home_team"] == team].sort_values("date")
        away_rows = df[df["away_team"] == team].sort_values("date")

        if home_rows.empty and away_rows.empty:
            continue

        # pick most recent row regardless of home/away
        last_home_date = home_rows["date"].iloc[-1] if not home_rows.empty else pd.Timestamp.min
        last_away_date = away_rows["date"].iloc[-1] if not away_rows.empty else pd.Timestamp.min

        if last_home_date >= last_away_date:
            row = home_rows.iloc[-1]
            side = 0  # home side
        else:
            row = away_rows.iloc[-1]
            side = 1  # away side

        snap = {}
        for key, (home_col, away_col) in TEAM_FEATURE_MAP.items():
            col = home_col if side == 0 else away_col
            snap[key] = row[col] if col in row.index else np.nan

        snapshots[team] = snap

    return snapshots


# ---------------------------------------------------------------------------
# 2026 host nation venue mapping (ground field → canonical parquet team name)
# Consistent with training data: host-nation matches in 2010/2014/2018/2022
# are encoded as neutral=False in master_matches.parquet.
# ---------------------------------------------------------------------------
GROUND_TO_HOST = {
    # Mexico
    "Mexico City":           "Mexico",
    "Guadalajara (Zapopan)": "Mexico",
    "Monterrey (Guadalupe)": "Mexico",
    # Canada
    "Toronto":               "Canada",
    "Vancouver":             "Canada",
    # United States — all remaining venues
    "Atlanta":                        "United States",
    "Boston (Foxborough)":            "United States",
    "Dallas (Arlington)":             "United States",
    "Houston":                        "United States",
    "Kansas City":                    "United States",
    "Los Angeles (Inglewood)":        "United States",
    "Miami (Miami Gardens)":          "United States",
    "New York/New Jersey (East Rutherford)": "United States",
    "Philadelphia":                   "United States",
    "San Francisco Bay Area (Santa Clara)":  "United States",
    "Seattle":                        "United States",
}

# 2022 World Cup group assignments (team canonical name → "Group X")
GROUP_2022 = {
    "Qatar": "Group A", "Ecuador": "Group A", "Senegal": "Group A", "Netherlands": "Group A",
    "England": "Group B", "Iran": "Group B", "United States": "Group B", "Wales": "Group B",
    "Argentina": "Group C", "Saudi Arabia": "Group C", "Mexico": "Group C", "Poland": "Group C",
    "France": "Group D", "Australia": "Group D", "Denmark": "Group D", "Tunisia": "Group D",
    "Spain": "Group E", "Costa Rica": "Group E", "Germany": "Group E", "Japan": "Group E",
    "Belgium": "Group F", "Canada": "Group F", "Morocco": "Group F", "Croatia": "Group F",
    "Brazil": "Group G", "Serbia": "Group G", "Switzerland": "Group G", "Cameroon": "Group G",
    "Portugal": "Group H", "Ghana": "Group H", "Uruguay": "Group H", "South Korea": "Group H",
}


# ---------------------------------------------------------------------------
# Build inference row from two team snapshots
# ---------------------------------------------------------------------------
def build_inference_row(team1_snap: dict, team2_snap: dict,
                        competition_tier: int, feat_cols: list,
                        neutral: int = 1) -> pd.DataFrame:
    """team1 = home side, team2 = away side."""
    home = team1_snap
    away = team2_snap

    row = {
        "home_elo_pre": home["elo"],
        "away_elo_pre": away["elo"],
        "elo_diff": home["elo"] - away["elo"],
        "home_fifa_rank": home["fifa_rank"],
        "away_fifa_rank": away["fifa_rank"],
        "neutral": neutral,
        "competition_tier": competition_tier,
        "home_last10_pts": home["last10_pts"],
        "home_last10_gd": home["last10_gd"],
        "home_last10_avg_opp_elo": home["last10_avg_opp_elo"],
        "home_last10_elo_delta": home["last10_elo_delta"],
        "home_last5_pts": home["last5_pts"],
        "home_last5_gd": home["last5_gd"],
        "home_last10_pts_weighted": home["last10_pts_weighted"],
        "home_last10_gd_weighted": home["last10_gd_weighted"],
        "away_last10_pts": away["last10_pts"],
        "away_last10_gd": away["last10_gd"],
        "away_last10_avg_opp_elo": away["last10_avg_opp_elo"],
        "away_last10_elo_delta": away["last10_elo_delta"],
        "away_last5_pts": away["last5_pts"],
        "away_last5_gd": away["last5_gd"],
        "away_last10_pts_weighted": away["last10_pts_weighted"],
        "away_last10_gd_weighted": away["last10_gd_weighted"],
        "home_last180d_pts_per_match": home["last180d_pts_per_match"],
        "home_last180d_gd_per_match": home["last180d_gd_per_match"],
        "home_last365d_matches_played": home["last365d_matches_played"],
        "home_last365d_pts_per_match": home["last365d_pts_per_match"],
        "away_last180d_pts_per_match": away["last180d_pts_per_match"],
        "away_last180d_gd_per_match": away["last180d_gd_per_match"],
        "away_last365d_matches_played": away["last365d_matches_played"],
        "away_last365d_pts_per_match": away["last365d_pts_per_match"],
        "home_squad_value": home["squad_value"],
        "away_squad_value": away["squad_value"],
        "home_gk_value": home["gk_value"],
        "away_gk_value": away["gk_value"],
        "home_def_value": home["def_value"],
        "away_def_value": away["def_value"],
        "home_mid_value": home["mid_value"],
        "away_mid_value": away["mid_value"],
        "home_atk_value": home["atk_value"],
        "away_atk_value": away["atk_value"],
        "def_vs_atk_matchup": home["def_value"] - away["atk_value"],
        "atk_vs_def_matchup": home["atk_value"] - away["def_value"],
    }
    return pd.DataFrame([row])[feat_cols]


# ---------------------------------------------------------------------------
# Feature importance from LR explanatory model
# ---------------------------------------------------------------------------
def compute_lr_feature_importance(expl_model, X_df: pd.DataFrame, feat_cols: list) -> list:
    """
    Returns top 5 factors by contribution to the home-win vs away-win log-odds,
    using LR (coef_H - coef_A) × scaled feature value. Positive = favors home.

    Raw features sharing a display label (home_elo_pre / away_elo_pre / elo_diff
    → "Elo rating") are summed into one factor so a label never appears twice.
    """
    try:
        imputer = expl_model.named_steps["imputer"]
        scaler = expl_model.named_steps["scaler"]
        lr = expl_model.named_steps["lr"]

        X_imp = imputer.transform(X_df)
        X_scaled = scaler.transform(X_imp)

        # coef_ shape: (n_classes, n_features); classes ['A', 'D', 'H']
        coef = lr.coef_
        if coef.shape[0] == 1:
            home_vs_away_coef = coef[0]
        else:
            home_vs_away_coef = coef[2] - coef[0]

        contributions = X_scaled[0] * home_vs_away_coef

        # Aggregate signed contributions by display label
        by_label: dict = {}
        for feat, contrib in zip(feat_cols, contributions):
            label = FEATURE_LABELS.get(feat, feat)
            entry = by_label.setdefault(label, {"total": 0.0, "feats": []})
            entry["total"] += float(contrib)
            entry["feats"].append((feat, float(contrib)))

        top = sorted(by_label.items(), key=lambda kv: abs(kv[1]["total"]), reverse=True)[:5]

        results = []
        for label, entry in top:
            total = entry["total"]
            # rawFeature = the largest single contributor within the group
            raw = max(entry["feats"], key=lambda fc: abs(fc[1]))[0]
            results.append({
                "feature": label,
                "rawFeature": raw,
                "direction": "favors_team1" if total > 0 else "favors_team2",
                "magnitude": round(abs(total), 4),
            })
        return results
    except Exception as e:
        log.warning(f"Feature importance computation failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Determine outcome label from probabilities
# ---------------------------------------------------------------------------
def get_outcome_label(p_team1: float, p_draw: float, p_team2: float) -> str:
    """Returns 'team1', 'draw', or 'team2'."""
    if p_team1 >= p_draw and p_team1 >= p_team2:
        return "team1"
    elif p_draw >= p_team1 and p_draw >= p_team2:
        return "draw"
    else:
        return "team2"


def get_confidence(max_prob: float) -> str:
    if max_prob < 0.45:
        return "low"
    elif max_prob <= 0.55:
        return "moderate"
    else:
        return "high"


def get_prediction_status(predicted: str, actual: str) -> str:
    if predicted == actual:
        return "correct"
    elif predicted == "draw" or actual == "draw":
        return "draw_miss"
    else:
        return "incorrect"


def outcome_from_row(row) -> str:
    """Convert 'H'/'D'/'A' outcome to 'team1'/'draw'/'team2'."""
    o = row["outcome"]
    if o == "H":
        return "team1"
    elif o == "D":
        return "draw"
    else:
        return "team2"


# ---------------------------------------------------------------------------
# Determine stage from round string (2026 fixtures)
# ---------------------------------------------------------------------------
def get_stage(round_str: str, group: str) -> str:
    r = round_str.lower()
    if "matchday" in r:
        return "group"
    elif "round of 32" in r:
        return "r32"
    elif "round of 16" in r:
        return "r16"
    elif "quarter" in r:
        return "qf"
    elif "semi" in r:
        return "sf"
    elif "third" in r or "3rd" in r:
        return "3rd"
    elif "final" in r:
        return "final"
    return "group"


def get_competition_tier(stage: str) -> int:
    return 2 if stage == "group" else 1


# ---------------------------------------------------------------------------
# Group standings computation (mirrors frontend computeGroupStandings logic)
# ---------------------------------------------------------------------------
def compute_group_standings_from_preds(preds: list) -> dict:
    """Return {group_name: [sorted_team_dicts]} from group stage predictions."""
    groups: dict = {}
    for m in preds:
        if not m.get("group") or m.get("status") != "predicted" or not m.get("probabilities"):
            continue
        g = m["group"]
        t1 = m["team1"]["name"]
        t2 = m["team2"]["name"]
        p = m["probabilities"]
        if g not in groups:
            groups[g] = {}
        if t1 not in groups[g]:
            groups[g][t1] = {"name": t1, "pts": 0, "gd": 0, "gf": 0, "played": 0,
                             "flag": m["team1"]["flag"],
                             "elo": m["teamStats"]["team1"]["eloRating"] if m.get("teamStats") else None}
        if t2 not in groups[g]:
            groups[g][t2] = {"name": t2, "pts": 0, "gd": 0, "gf": 0, "played": 0,
                             "flag": m["team2"]["flag"],
                             "elo": m["teamStats"]["team2"]["eloRating"] if m.get("teamStats") else None}
        s1, s2 = groups[g][t1], groups[g][t2]
        s1["played"] += 1
        s2["played"] += 1
        p1, pd, p2 = p["team1Win"], p["draw"], p["team2Win"]
        if p1 >= pd and p1 >= p2:
            s1["pts"] += 3; s1["gd"] += 1; s2["gd"] -= 1; s1["gf"] += 1
        elif pd >= p1 and pd >= p2:
            s1["pts"] += 1; s2["pts"] += 1
        else:
            s2["pts"] += 3; s2["gd"] += 1; s1["gd"] -= 1; s2["gf"] += 1
    result = {}
    for g, table in groups.items():
        result[g] = sorted(table.values(), key=lambda x: (-x["pts"], -x["gd"], -x["gf"]))
    return result


# ---------------------------------------------------------------------------
# FIFA 2026 official third-place bracket structure.
#
# THIRD_PLACE_QUALIFYING_GROUPS_2026: the 8 of 12 groups whose 3rd-place teams
# advance to the Round of 32, as defined by FIFA's official 2026 bracket design.
# Groups G, J, K, L are not allocated a guaranteed R32 slot in this bracket.
#
# THIRD_PLACE_ALLOC_2026: maps the frozenset of qualifying group letters to
# {fixture_number: group_letter}, specifying which group's 3rd-place team fills
# each slot per FIFA's published allocation table for the 2026 format.
# ---------------------------------------------------------------------------
THIRD_PLACE_QUALIFYING_GROUPS_2026: frozenset = frozenset("ABCDEFHI")

THIRD_PLACE_ALLOC_2026: dict[frozenset, dict[int, str]] = {
    frozenset("ABCDEFHI"): {
        74: "C", 77: "F", 79: "H", 80: "I",
        81: "B", 82: "A", 85: "E", 87: "D",
    },
}


def resolve_bracket_pos(pos: str, standings: dict, third_place: list, winners: dict,
                        losers: dict | None = None,
                        slot_assignment: dict | None = None, f_num: int | None = None):
    """Resolve a position string to a team dict, or None if unresolvable."""
    import re
    m = re.match(r"^([12])([A-L])$", pos)
    if m:
        rank = int(m.group(1)) - 1
        group = f"Group {m.group(2)}"
        table = standings.get(group, [])
        return dict(table[rank]) if rank < len(table) else None
    m = re.match(r"^3([A-L/]+)$", pos)
    if m:
        # Use pre-computed FIFA allocation table when available.
        if slot_assignment is not None and f_num is not None and f_num in slot_assignment:
            return dict(slot_assignment[f_num])
        # Fallback: greedy scan of sorted third_place list.
        groups = [f"Group {g}" for g in m.group(1).split("/")]
        for t in third_place:
            if t.get("_group") in groups and not t.get("_used"):
                t["_used"] = True
                return t
        return None
    m = re.match(r"^W(\d+)$", pos)
    if m:
        return winners.get(int(m.group(1)))
    m = re.match(r"^L(\d+)$", pos)
    if m:
        return (losers or {}).get(int(m.group(1)))
    return None


def simulate_bracket_with_model(
    fixtures_data: dict, preds_2026: list,
    model, expl_model, feat_cols,
    snapshots: dict, name_map: dict,
) -> list:
    """Simulate the full knockout bracket using the ML model (competition_tier=1)."""
    standings = compute_group_standings_from_preds(preds_2026)

    all_canonicals_snap = list(snapshots.keys())

    # Build third-place pool with Elo for ranking tiebreaks.
    group_to_3rd: dict[str, dict] = {}
    third_place_pool: list[dict] = []
    for group, table in standings.items():
        if len(table) >= 3:
            t = dict(table[2])
            t["_group"] = group
            t["_used"] = False
            gl = group.split()[-1]  # "Group A" → "A"
            t_canon = canonicalize(t["name"], name_map, all_canonicals_snap)
            if t_canon and t_canon in snapshots and not np.isnan(snapshots[t_canon]["elo"]):
                t["_elo"] = float(snapshots[t_canon]["elo"])
            else:
                t["_elo"] = 0.0
            third_place_pool.append(t)
            group_to_3rd[gl] = t

    # Use the FIFA 2026 official set of qualifying groups directly.
    # Ranking individual 3rd-place teams by Elo/FIFA rank doesn't match the
    # official bracket design (some lower-ranked teams are guaranteed slots).
    slot_assignment: dict[int, dict] = {}
    qualifying_letters = THIRD_PLACE_QUALIFYING_GROUPS_2026
    if qualifying_letters in THIRD_PLACE_ALLOC_2026:
        log.info(f"Third-place allocation: using FIFA 2026 table for groups {sorted(qualifying_letters)}")
        for slot_num, gl in THIRD_PLACE_ALLOC_2026[qualifying_letters].items():
            if gl in group_to_3rd:
                slot_assignment[slot_num] = group_to_3rd[gl]

    # third_place list used only for greedy fallback when slot_assignment misses a slot.
    # Sort by pts→gd→gf→elo so the fallback is at least reasonable.
    third_place_pool.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], -x.get("_elo", 0)))
    third_place = [t for t in third_place_pool if t["_group"].split()[-1] in qualifying_letters]

    all_canonicals = list(snapshots.keys())
    knockout_fixtures = [f for f in fixtures_data["matches"] if not f.get("group")]
    ROUND_ORDER = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final",
                   "Match for third place", "Final"]
    winners: dict = {}
    losers: dict = {}
    results = []

    for round_name in ROUND_ORDER:
        for f in [fx for fx in knockout_fixtures if fx.get("round") == round_name]:
            t1_pos = f.get("team1", "")
            t2_pos = f.get("team2", "")
            f_num = f.get("num")
            if f_num:
                match_id = f"bracket_{f_num}"
            elif round_name == "Final":
                match_id = "bracket_final"
            else:
                match_id = "bracket_3rd"

            team1_dict = resolve_bracket_pos(t1_pos, standings, third_place, winners, losers,
                                             slot_assignment=slot_assignment, f_num=f_num)
            team2_dict = resolve_bracket_pos(t2_pos, standings, third_place, winners, losers,
                                             slot_assignment=slot_assignment, f_num=f_num)

            stage = get_stage(round_name, "")
            tier = get_competition_tier(stage)

            base = {
                "matchId": match_id,
                "date": f.get("date", ""),
                "time": f.get("time", ""),
                "venue": f.get("ground", ""),
                "group": "",
                "round": round_name,
                "stage": stage,
            }

            if not team1_dict or not team2_dict:
                base["team1"] = {"name": t1_pos, "flag": "🏳️"}
                base["team2"] = {"name": t2_pos, "flag": "🏳️"}
                base["status"] = "pending"
                base["neutral"] = 1
                base["probabilities"] = None
                base["predictedOutcome"] = None
                base["confidence"] = None
                base["shapFeatures"] = []
                base["teamStats"] = None
                results.append(base)
                continue

            t1_name = team1_dict["name"]
            t2_name = team2_dict["name"]
            t1_canon = canonicalize(t1_name, name_map, all_canonicals)
            t2_canon = canonicalize(t2_name, name_map, all_canonicals)

            base["team1"] = {"name": t1_name, "flag": team1_dict.get("flag", get_flag(t1_name))}
            base["team2"] = {"name": t2_name, "flag": team2_dict.get("flag", get_flag(t2_name))}

            if t1_canon not in snapshots or t2_canon not in snapshots:
                base["status"] = "no_data"
                base["neutral"] = 1
                base["probabilities"] = None
                base["predictedOutcome"] = None
                base["confidence"] = None
                base["shapFeatures"] = []
                base["teamStats"] = None
                results.append(base)
                continue

            ground = f.get("ground", "")
            venue_host = GROUND_TO_HOST.get(ground)
            neutral_flag = 1
            swapped = False
            if venue_host:
                if t1_canon == venue_host:
                    neutral_flag = 0
                elif t2_canon == venue_host:
                    neutral_flag = 0
                    swapped = True

            snap_home = snapshots[t2_canon] if swapped else snapshots[t1_canon]
            snap_away = snapshots[t1_canon] if swapped else snapshots[t2_canon]

            X = build_inference_row(snap_home, snap_away, tier, feat_cols, neutral=neutral_flag)
            proba = model.predict_proba(X)[0]
            p_home_win = float(proba[2])
            p_draw     = float(proba[1])
            p_away_win = float(proba[0])

            if swapped:
                p_team1, p_team2 = p_away_win, p_home_win
            else:
                p_team1, p_team2 = p_home_win, p_away_win

            predicted = get_outcome_label(p_team1, p_draw, p_team2)
            max_p = max(p_team1, p_draw, p_team2)

            raw_shap = compute_lr_feature_importance(expl_model, X, feat_cols)
            if swapped:
                flip = {"favors_team1": "favors_team2", "favors_team2": "favors_team1"}
                shap_feats = [{**sf, "direction": flip.get(sf["direction"], sf["direction"])} for sf in raw_shap]
            else:
                shap_feats = raw_shap

            # Track winner and loser for downstream rounds
            if predicted == "team1":
                win_dict = team1_dict
            elif predicted == "team2":
                win_dict = team2_dict
            else:
                win_dict = team1_dict if p_team1 >= p_team2 else team2_dict
            lose_dict = team2_dict if win_dict.get("name") == team1_dict.get("name") else team1_dict
            if f_num:
                winners[f_num] = win_dict
                losers[f_num] = lose_dict

            def _m(v):
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return None
                return round(float(v) / 1_000_000, 2)

            snap1 = snapshots[t1_canon]
            snap2 = snapshots[t2_canon]
            base.update({
                "status": "predicted",
                "neutral": neutral_flag,
                "probabilities": {
                    "team1Win": round(p_team1, 4),
                    "draw":     round(p_draw,   4),
                    "team2Win": round(p_team2,  4),
                },
                "predictedOutcome": predicted,
                "confidence": get_confidence(max_p),
                "shapFeatures": shap_feats,
                "teamStats": {
                    "team1": {
                        "eloRating":  round(float(snap1["elo"]),       1) if not np.isnan(snap1["elo"])       else None,
                        "fifaRank":   int(snap1["fifa_rank"])              if not np.isnan(snap1["fifa_rank"]) else None,
                        "last10Pts":  int(snap1["last10_pts"])             if not np.isnan(snap1["last10_pts"])else None,
                        "last5Gd":    int(snap1["last5_gd"])               if not np.isnan(snap1["last5_gd"])  else None,
                        "squadValueM": _m(snap1["squad_value"]),
                    },
                    "team2": {
                        "eloRating":  round(float(snap2["elo"]),       1) if not np.isnan(snap2["elo"])       else None,
                        "fifaRank":   int(snap2["fifa_rank"])              if not np.isnan(snap2["fifa_rank"]) else None,
                        "last10Pts":  int(snap2["last10_pts"])             if not np.isnan(snap2["last10_pts"])else None,
                        "last5Gd":    int(snap2["last5_gd"])               if not np.isnan(snap2["last5_gd"])  else None,
                        "squadValueM": _m(snap2["squad_value"]),
                    },
                },
            })
            results.append(base)

    predicted_count = sum(1 for r in results if r["status"] == "predicted")
    log.info(f"Bracket: {predicted_count}/{len(results)} matches predicted")
    return results


# ---------------------------------------------------------------------------
# 2026 predictions
# ---------------------------------------------------------------------------
def generate_2026_predictions(model, expl_model, le, feat_cols,
                               snapshots: dict, name_map: dict) -> list:
    fixture_path = os.path.join(DATA_DIR, "raw", "openfootball", "worldcup.json")
    with open(fixture_path) as f:
        data = json.load(f)

    all_canonicals = list(snapshots.keys())
    results = []

    for i, match in enumerate(data["matches"]):
        match_id = f"2026_{i+1:03d}"
        team1_raw = match.get("team1", "")
        team2_raw = match.get("team2", "")
        round_str = match.get("round", "")
        group = match.get("group", "")
        stage = get_stage(round_str, group)
        tier = get_competition_tier(stage)

        # Knockout bracket placeholders (e.g. "2A", "1B") — no prediction possible
        is_group_match = bool(group)
        team1_is_placeholder = len(team1_raw) <= 3 and not team1_raw.isalpha()
        team2_is_placeholder = len(team2_raw) <= 3 and not team2_raw.isalpha()

        base = {
            "matchId": match_id,
            "date": match.get("date", ""),
            "time": match.get("time", ""),
            "venue": match.get("ground", ""),
            "group": group,
            "round": round_str,
            "stage": stage,
            "team1": {"name": team1_raw, "flag": get_flag(team1_raw)},
            "team2": {"name": team2_raw, "flag": get_flag(team2_raw)},
        }

        if team1_is_placeholder or team2_is_placeholder:
            base["status"] = "pending"
            base["probabilities"] = None
            base["predictedOutcome"] = None
            base["confidence"] = None
            base["shap_features"] = []
            base["teamStats"] = None
            results.append(base)
            continue

        # Canonicalize names
        t1_canon = canonicalize(team1_raw, name_map, all_canonicals)
        t2_canon = canonicalize(team2_raw, name_map, all_canonicals)

        if t1_canon not in snapshots or t2_canon not in snapshots:
            missing = []
            if t1_canon not in snapshots:
                missing.append(team1_raw)
            if t2_canon not in snapshots:
                missing.append(team2_raw)
            log.warning(f"No snapshot for: {missing} — match {match_id} skipped prediction")
            base["status"] = "no_data"
            base["probabilities"] = None
            base["predictedOutcome"] = None
            base["confidence"] = None
            base["shap_features"] = []
            base["teamStats"] = None
            results.append(base)
            continue

        # Determine neutral flag and home/away assignment.
        # When a host nation is playing in their own country, treat as non-neutral
        # (consistent with how 2010/2014/2018/2022 host matches are encoded in training data).
        ground = match.get("ground", "")
        venue_host = GROUND_TO_HOST.get(ground)
        neutral_flag = 1
        # swapped=True means we put t2 in the "home" slot of the feature vector;
        # probabilities and shap directions are flipped back before output.
        swapped = False
        if venue_host is not None:
            if t1_canon == venue_host:
                neutral_flag = 0          # team1 is already home, no swap needed
            elif t2_canon == venue_host:
                neutral_flag = 0
                swapped = True            # team2 is the host; put them in home slot

        if swapped:
            snap_home, snap_away = snapshots[t2_canon], snapshots[t1_canon]
        else:
            snap_home, snap_away = snapshots[t1_canon], snapshots[t2_canon]

        X = build_inference_row(snap_home, snap_away, tier, feat_cols, neutral=neutral_flag)
        proba = model.predict_proba(X)[0]
        # Classes: ['A', 'D', 'H'] → index 0=Away win, 1=Draw, 2=Home win
        p_home_win = float(proba[2])
        p_draw     = float(proba[1])
        p_away_win = float(proba[0])

        # Map back to output team1/team2 perspective (undo swap if needed)
        if swapped:
            p_team1, p_team2 = p_away_win, p_home_win
        else:
            p_team1, p_team2 = p_home_win, p_away_win

        predicted = get_outcome_label(p_team1, p_draw, p_team2)
        max_p = max(p_team1, p_draw, p_team2)

        # Compute importance from the home/away-ordered feature vector; flip
        # favors_team1/team2 labels if we swapped to reflect output ordering.
        shap_feats_raw = compute_lr_feature_importance(expl_model, X, feat_cols)
        if swapped:
            flip = {"favors_team1": "favors_team2", "favors_team2": "favors_team1"}
            shap_feats = [{**f, "direction": flip.get(f["direction"], f["direction"])}
                          for f in shap_feats_raw]
        else:
            shap_feats = shap_feats_raw

        def _m(v):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return None
            return round(float(v) / 1_000_000, 2)

        snap1 = snapshots[t1_canon]
        snap2 = snapshots[t2_canon]
        base.update({
            "status": "predicted",
            "neutral": neutral_flag,
            "probabilities": {
                "team1Win": round(p_team1, 4),
                "draw": round(p_draw, 4),
                "team2Win": round(p_team2, 4),
            },
            "predictedOutcome": predicted,
            "confidence": get_confidence(max_p),
            "shapFeatures": shap_feats,
            "teamStats": {
                "team1": {
                    "eloRating": round(float(snap1["elo"]), 1) if not np.isnan(snap1["elo"]) else None,
                    "fifaRank": int(snap1["fifa_rank"]) if not np.isnan(snap1["fifa_rank"]) else None,
                    "last10Pts": int(snap1["last10_pts"]) if not np.isnan(snap1["last10_pts"]) else None,
                    "last5Gd": int(snap1["last5_gd"]) if not np.isnan(snap1["last5_gd"]) else None,
                    "squadValueM": _m(snap1["squad_value"]),
                },
                "team2": {
                    "eloRating": round(float(snap2["elo"]), 1) if not np.isnan(snap2["elo"]) else None,
                    "fifaRank": int(snap2["fifa_rank"]) if not np.isnan(snap2["fifa_rank"]) else None,
                    "last10Pts": int(snap2["last10_pts"]) if not np.isnan(snap2["last10_pts"]) else None,
                    "last5Gd": int(snap2["last5_gd"]) if not np.isnan(snap2["last5_gd"]) else None,
                    "squadValueM": _m(snap2["squad_value"]),
                },
            },
        })
        results.append(base)

    log.info(f"2026: {sum(1 for r in results if r['status'] == 'predicted')} predicted, "
             f"{sum(1 for r in results if r['status'] == 'pending')} pending")
    return results


# ---------------------------------------------------------------------------
# 2022 predictions
# ---------------------------------------------------------------------------
def generate_2022_predictions(df: pd.DataFrame, model, expl_model, le, feat_cols) -> list:
    wc2022 = df[
        (df["date"] >= "2022-11-20") &
        (df["match_stage"].str.startswith("wc_"))
    ].copy().reset_index(drop=True)

    log.info(f"2022 WC matches found: {len(wc2022)}")

    # Add elo_diff
    wc2022["elo_diff"] = wc2022["home_elo_pre"] - wc2022["away_elo_pre"]

    # Build feature matrix (these rows already have leakage-free pre-match features)
    X = wc2022[feat_cols].copy()
    probas = model.predict_proba(X)

    # Build group labels for 2022 — from match_stage + tournament ordering
    # We'll assign group from the first 48 matches being group stage
    stage_to_display = {
        "wc_group": "Group Stage",
        "wc_r16": "Round of 16",
        "wc_qf": "Quarter-final",
        "wc_sf": "Semi-final",
        "wc_3rd": "Match for third place",
        "wc_final": "Final",
        "wc_r32": "Round of 32",
    }

    results = []
    for idx, (_, row) in enumerate(wc2022.iterrows()):
        proba = probas[idx]
        p_team2 = float(proba[0])  # A = away win
        p_draw = float(proba[1])   # D = draw
        p_team1 = float(proba[2])  # H = home win

        predicted = get_outcome_label(p_team1, p_draw, p_team2)
        actual = outcome_from_row(row)
        status = get_prediction_status(predicted, actual)
        max_p = max(p_team1, p_draw, p_team2)

        team1_name = str(row["home_team"])
        team2_name = str(row["away_team"])
        stage = str(row["match_stage"])

        X_single = pd.DataFrame([X.iloc[idx]])
        shap_feats = compute_lr_feature_importance(expl_model, X_single, feat_cols)

        def _m(v):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return None
            return round(float(v) / 1_000_000, 2)

        def _safe_int(v):
            try:
                if np.isnan(v):
                    return None
                return int(v)
            except Exception:
                return None

        def _safe_float(v):
            try:
                if np.isnan(v):
                    return None
                return round(float(v), 1)
            except Exception:
                return None

        results.append({
            "matchId": f"2022_{idx+1:03d}",
            "date": str(row["date"])[:10],
            "group": GROUP_2022.get(team1_name, GROUP_2022.get(team2_name, "")),
            "round": stage_to_display.get(stage, stage),
            "stage": stage.replace("wc_", ""),
            "team1": {"name": team1_name, "flag": get_flag(team1_name)},
            "team2": {"name": team2_name, "flag": get_flag(team2_name)},
            "probabilities": {
                "team1Win": round(p_team1, 4),
                "draw": round(p_draw, 4),
                "team2Win": round(p_team2, 4),
            },
            "predictedOutcome": predicted,
            "actualOutcome": actual,
            "actualScore": {
                "team1": _safe_int(row["home_score"]),
                "team2": _safe_int(row["away_score"]),
            },
            "predictionStatus": status,
            "confidence": get_confidence(max_p),
            "shapFeatures": shap_feats,
            "teamStats": {
                "team1": {
                    "eloRating": _safe_float(row["home_elo_pre"]),
                    "fifaRank": _safe_int(row["home_fifa_rank"]),
                    "last10Pts": _safe_int(row["home_last10_pts"]),
                    "last5Gd": _safe_int(row["home_last5_gd"]),
                    "squadValueM": _m(row["home_squad_value"]),
                },
                "team2": {
                    "eloRating": _safe_float(row["away_elo_pre"]),
                    "fifaRank": _safe_int(row["away_fifa_rank"]),
                    "last10Pts": _safe_int(row["away_last10_pts"]),
                    "last5Gd": _safe_int(row["away_last5_gd"]),
                    "squadValueM": _m(row["away_squad_value"]),
                },
            },
        })

    correct = sum(1 for r in results if r["predictionStatus"] == "correct")
    log.info(f"2022: {correct}/{len(results)} correct ({100*correct/len(results):.1f}%)")
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    model, expl_model, le, feat_cols = load_artifacts()

    log.info("Loading master_matches.parquet...")
    df = pd.read_parquet(os.path.join(DATA_DIR, "final", "master_matches.parquet"))
    df["date"] = pd.to_datetime(df["date"])
    log.info(f"Parquet loaded: {len(df)} rows")

    name_map = build_name_map()
    log.info(f"Team name map loaded: {len(name_map)} aliases")

    log.info("Building team feature snapshots...")
    snapshots = build_team_snapshots(df)
    log.info(f"Snapshots built for {len(snapshots)} teams")

    override_fifa_ranks(snapshots, name_map)

    log.info("Generating 2026 predictions...")
    preds_2026 = generate_2026_predictions(model, expl_model, le, feat_cols, snapshots, name_map)

    fixture_path = os.path.join(DATA_DIR, "raw", "openfootball", "worldcup.json")
    with open(fixture_path) as f:
        fixtures_data = json.load(f)
    log.info("Simulating bracket with ML model...")
    bracket_matches = simulate_bracket_with_model(
        fixtures_data, preds_2026, model, expl_model, feat_cols, snapshots, name_map
    )

    log.info("Generating 2022 predictions...")
    preds_2022 = generate_2022_predictions(df, model, expl_model, le, feat_cols)

    # Compute 2022 summary stats
    correct = sum(1 for r in preds_2022 if r["predictionStatus"] == "correct")
    incorrect = sum(1 for r in preds_2022 if r["predictionStatus"] == "incorrect")
    draw_miss = sum(1 for r in preds_2022 if r["predictionStatus"] == "draw_miss")
    accuracy = correct / len(preds_2022) if preds_2022 else 0

    out_2026 = {
        "generatedAt": pd.Timestamp.now().isoformat(),
        "matchCount": len(preds_2026),
        "modelAccuracy": 0.578,
        "matches": preds_2026,
        "bracketMatches": bracket_matches,
    }
    out_2022 = {
        "generatedAt": pd.Timestamp.now().isoformat(),
        "matchCount": len(preds_2022),
        "modelAccuracy": 0.578,
        "computedAccuracy": round(accuracy, 4),
        "summary": {
            "correct": correct,
            "incorrect": incorrect,
            "drawMiss": draw_miss,
            "total": len(preds_2022),
        },
        "matches": preds_2022,
    }

    path_2026 = os.path.join(CACHE_DIR, "predictions_2026.json")
    path_2022 = os.path.join(CACHE_DIR, "predictions_2022.json")

    with open(path_2026, "w") as f:
        json.dump(out_2026, f, indent=2, default=str)
    with open(path_2022, "w") as f:
        json.dump(out_2022, f, indent=2, default=str)

    log.info(f"Saved: {path_2026}")
    log.info(f"Saved: {path_2022}")
    log.info("Done.")


if __name__ == "__main__":
    main()
