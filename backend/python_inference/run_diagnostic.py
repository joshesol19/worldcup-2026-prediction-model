"""
D1: Feature coverage audit for all 2026 group-stage fixtures.
D2: Full SHAP/LR contribution vector for Mexico vs South Africa and South Korea vs Czech Republic.

Outputs:
  backend/cache/feature_audit.json
  backend/cache/shap_dump.json
"""
import os
import sys
import json
import warnings
import logging
import difflib
import numpy as np
import pandas as pd
import joblib

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.WARNING)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CACHE_DIR = os.path.join(SCRIPT_DIR, "..", "cache")

STALE_CUTOFF = pd.Timestamp("2024-01-01")  # >18 months before Jun 2026

# ---------------------------------------------------------------------------
# Duplicate of inference helpers (keep self-contained)
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

# Map snapshot key → model feature columns (home/away)
SNAP_TO_FEAT = {
    "elo":                   ("home_elo_pre",              "away_elo_pre"),
    "fifa_rank":             ("home_fifa_rank",             "away_fifa_rank"),
    "last10_pts":            ("home_last10_pts",            "away_last10_pts"),
    "last10_gd":             ("home_last10_gd",             "away_last10_gd"),
    "last10_avg_opp_elo":    ("home_last10_avg_opp_elo",   "away_last10_avg_opp_elo"),
    "last10_elo_delta":      ("home_last10_elo_delta",      "away_last10_elo_delta"),
    "last5_pts":             ("home_last5_pts",             "away_last5_pts"),
    "last5_gd":              ("home_last5_gd",              "away_last5_gd"),
    "last10_pts_weighted":   ("home_last10_pts_weighted",   "away_last10_pts_weighted"),
    "last10_gd_weighted":    ("home_last10_gd_weighted",    "away_last10_gd_weighted"),
    "last180d_pts_per_match":("home_last180d_pts_per_match","away_last180d_pts_per_match"),
    "last180d_gd_per_match": ("home_last180d_gd_per_match", "away_last180d_gd_per_match"),
    "last365d_matches_played":("home_last365d_matches_played","away_last365d_matches_played"),
    "last365d_pts_per_match":("home_last365d_pts_per_match","away_last365d_pts_per_match"),
    "squad_value":           ("home_squad_value",           "away_squad_value"),
    "gk_value":              ("home_gk_value",              "away_gk_value"),
    "def_value":             ("home_def_value",             "away_def_value"),
    "mid_value":             ("home_mid_value",             "away_mid_value"),
    "atk_value":             ("home_atk_value",             "away_atk_value"),
}


def build_name_map():
    path = os.path.join(DATA_DIR, "processed", "team_name_map.csv")
    df = pd.read_csv(path)
    return dict(zip(df["alias"].str.strip(), df["canonical"].str.strip()))


def canonicalize(name, mapping, all_canonicals):
    name = name.strip()
    if name in mapping:
        return mapping[name], "exact_alias"
    if name in all_canonicals:
        return name, "direct_canonical"
    close = difflib.get_close_matches(name, list(mapping.keys()) + all_canonicals, n=1, cutoff=0.7)
    if close:
        matched = close[0]
        canon = mapping.get(matched, matched)
        return canon, f"fuzzy:{matched}"
    return None, "failed"


def build_team_snapshots(df):
    snapshots = {}
    snapshot_dates = {}
    all_teams = set(df["home_team"].unique()) | set(df["away_team"].unique())

    for team in all_teams:
        home_rows = df[df["home_team"] == team].sort_values("date")
        away_rows = df[df["away_team"] == team].sort_values("date")

        if home_rows.empty and away_rows.empty:
            continue

        last_home_date = home_rows["date"].iloc[-1] if not home_rows.empty else pd.Timestamp.min
        last_away_date = away_rows["date"].iloc[-1] if not away_rows.empty else pd.Timestamp.min

        if last_home_date >= last_away_date:
            row = home_rows.iloc[-1]
            side = 0
        else:
            row = away_rows.iloc[-1]
            side = 1

        snap = {}
        for key, (home_col, away_col) in TEAM_FEATURE_MAP.items():
            col = home_col if side == 0 else away_col
            snap[key] = row[col] if col in row.index else np.nan

        snapshots[team] = snap
        snapshot_dates[team] = row["date"]

    return snapshots, snapshot_dates


def build_inference_row(snap1, snap2, tier, feat_cols):
    row = {
        "home_elo_pre": snap1["elo"],
        "away_elo_pre": snap2["elo"],
        "elo_diff": snap1["elo"] - snap2["elo"],
        "home_fifa_rank": snap1["fifa_rank"],
        "away_fifa_rank": snap2["fifa_rank"],
        "neutral": 1,
        "competition_tier": tier,
        "home_last10_pts": snap1["last10_pts"],
        "home_last10_gd": snap1["last10_gd"],
        "home_last10_avg_opp_elo": snap1["last10_avg_opp_elo"],
        "home_last10_elo_delta": snap1["last10_elo_delta"],
        "home_last5_pts": snap1["last5_pts"],
        "home_last5_gd": snap1["last5_gd"],
        "home_last10_pts_weighted": snap1["last10_pts_weighted"],
        "home_last10_gd_weighted": snap1["last10_gd_weighted"],
        "away_last10_pts": snap2["last10_pts"],
        "away_last10_gd": snap2["last10_gd"],
        "away_last10_avg_opp_elo": snap2["last10_avg_opp_elo"],
        "away_last10_elo_delta": snap2["last10_elo_delta"],
        "away_last5_pts": snap2["last5_pts"],
        "away_last5_gd": snap2["last5_gd"],
        "away_last10_pts_weighted": snap2["last10_pts_weighted"],
        "away_last10_gd_weighted": snap2["last10_gd_weighted"],
        "home_last180d_pts_per_match": snap1["last180d_pts_per_match"],
        "home_last180d_gd_per_match": snap1["last180d_gd_per_match"],
        "home_last365d_matches_played": snap1["last365d_matches_played"],
        "home_last365d_pts_per_match": snap1["last365d_pts_per_match"],
        "away_last180d_pts_per_match": snap2["last180d_pts_per_match"],
        "away_last180d_gd_per_match": snap2["last180d_gd_per_match"],
        "away_last365d_matches_played": snap2["last365d_matches_played"],
        "away_last365d_pts_per_match": snap2["last365d_pts_per_match"],
        "home_squad_value": snap1["squad_value"],
        "away_squad_value": snap2["squad_value"],
        "home_gk_value": snap1["gk_value"],
        "away_gk_value": snap2["gk_value"],
        "home_def_value": snap1["def_value"],
        "away_def_value": snap2["def_value"],
        "home_mid_value": snap1["mid_value"],
        "away_mid_value": snap2["mid_value"],
        "home_atk_value": snap1["atk_value"],
        "away_atk_value": snap2["atk_value"],
        "def_vs_atk_matchup": snap1["def_value"] - snap2["atk_value"],
        "atk_vs_def_matchup": snap1["atk_value"] - snap2["def_value"],
    }
    return pd.DataFrame([row])[feat_cols]


def get_imputed_features(X_df, model, feat_cols):
    """Return list of feature names that were NaN before imputation."""
    # The inner pipeline inside CalibratedClassifierCV has the imputer
    try:
        inner_pipeline = model.calibrated_classifiers_[0].estimator
        imputer = inner_pipeline.named_steps["imputer"]
        nan_mask = X_df.isnull().values[0]
        return [feat_cols[i] for i, is_nan in enumerate(nan_mask) if is_nan]
    except Exception as e:
        return []


def compute_full_lr_contributions(expl_model, X_df, feat_cols):
    """Return all 43 feature contributions for the predicted class (all 3 classes)."""
    imputer = expl_model.named_steps["imputer"]
    scaler = expl_model.named_steps["scaler"]
    lr = expl_model.named_steps["lr"]

    X_imp = imputer.transform(X_df)
    X_scaled = scaler.transform(X_imp)
    coef = lr.coef_  # shape (3, 43) for multiclass or (1, 43) for binary

    result = {}
    classes = ["A", "D", "H"]  # Away win, Draw, Home win
    for ci, cls in enumerate(classes if coef.shape[0] > 1 else ["binary"]):
        c = coef[ci] if coef.shape[0] > 1 else coef[0]
        contributions = X_scaled[0] * c
        result[cls] = {feat_cols[i]: float(contributions[i]) for i in range(len(feat_cols))}
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading artifacts...")
    model = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_model_final.joblib"))
    expl_model = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_model_explanatory.joblib"))
    feat_cols = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_feature_cols.joblib"))
    le = joblib.load(os.path.join(MODELS_DIR, "worldcup_2026_label_encoder.joblib"))

    print("Loading parquet...")
    df = pd.read_parquet(os.path.join(DATA_DIR, "final", "master_matches.parquet"))
    df["date"] = pd.to_datetime(df["date"])

    name_map = build_name_map()
    all_canonicals = list(set(df["home_team"].unique()) | set(df["away_team"].unique()))

    print("Building snapshots...")
    snapshots, snapshot_dates = build_team_snapshots(df)

    fixture_path = os.path.join(DATA_DIR, "raw", "openfootball", "worldcup.json")
    with open(fixture_path) as f:
        fixture_data = json.load(f)

    matches = fixture_data["matches"]
    def is_placeholder(name):
        return len(name) <= 3 and not name.isalpha()

    # Only group-stage matches with real (non-placeholder) team names
    group_matches = [
        m for m in matches
        if m.get("group")
        and not is_placeholder(m.get("team1", ""))
        and not is_placeholder(m.get("team2", ""))
    ]

    print(f"Group matches to audit: {len(group_matches)}")

    # -------------------------------------------------------------------------
    # D1: Feature coverage audit
    # -------------------------------------------------------------------------
    audit_entries = []

    # Track summary stats
    full_coverage_count = 0
    any_imputed_count = 0
    name_fail_teams = set()
    stale_teams = set()  # teams where latest parquet row < Jan 2024

    for m in group_matches:
        t1_raw = m["team1"]
        t2_raw = m["team2"]
        group = m.get("group", "")
        round_str = m.get("round", "")
        date = m.get("date", "")

        t1_canon, t1_res = canonicalize(t1_raw, name_map, all_canonicals)
        t2_canon, t2_res = canonicalize(t2_raw, name_map, all_canonicals)

        entry = {
            "date": date,
            "group": group,
            "round": round_str,
            "team1_raw": t1_raw,
            "team2_raw": t2_raw,
            "team1_canonical": t1_canon,
            "team2_canonical": t2_canon,
            "team1_name_resolution": t1_res,
            "team2_name_resolution": t2_res,
        }

        if t1_canon is None:
            name_fail_teams.add(t1_raw)
        if t2_canon is None:
            name_fail_teams.add(t2_raw)

        if t1_canon is None or t2_canon is None or t1_canon not in snapshots or t2_canon not in snapshots:
            entry["status"] = "name_resolution_failed"
            entry["features"] = {}
            entry["imputed_features"] = []
            entry["stale_team1"] = None
            entry["stale_team2"] = None
            audit_entries.append(entry)
            continue

        snap1 = snapshots[t1_canon]
        snap2 = snapshots[t2_canon]
        date1 = snapshot_dates[t1_canon]
        date2 = snapshot_dates[t2_canon]

        t1_stale = date1 < STALE_CUTOFF
        t2_stale = date2 < STALE_CUTOFF
        if t1_stale:
            stale_teams.add(t1_canon)
        if t2_stale:
            stale_teams.add(t2_canon)

        entry["team1_snapshot_date"] = str(date1)[:10]
        entry["team2_snapshot_date"] = str(date2)[:10]
        entry["team1_stale"] = t1_stale
        entry["team2_stale"] = t2_stale

        X = build_inference_row(snap1, snap2, 2, feat_cols)
        imputed = get_imputed_features(X, model, feat_cols)

        # Per-feature coverage
        feat_coverage = {}
        for feat in feat_cols:
            val = X[feat].iloc[0]
            is_nan = bool(pd.isna(val))
            feat_coverage[feat] = {
                "value": None if is_nan else round(float(val), 6),
                "nan": is_nan,
                "imputed": feat in imputed,
            }

        entry["features"] = feat_coverage
        entry["imputed_features"] = imputed
        entry["status"] = "ok"

        if len(imputed) == 0:
            full_coverage_count += 1
        else:
            any_imputed_count += 1

        audit_entries.append(entry)

    # -------------------------------------------------------------------------
    # Identify features that are always imputed (constant NaN) vs sometimes
    # -------------------------------------------------------------------------
    # For each feature, count how many fixtures had it imputed
    imputed_freq = {}
    for feat in feat_cols:
        count = sum(1 for e in audit_entries if feat in e.get("imputed_features", []))
        if count > 0:
            imputed_freq[feat] = count

    # Also identify features that are constant across the 2026 fixture set
    all_values_by_feat = {}
    for feat in feat_cols:
        vals = []
        for e in audit_entries:
            if "features" in e and feat in e["features"]:
                v = e["features"][feat]["value"]
                if v is not None:
                    vals.append(v)
        all_values_by_feat[feat] = vals

    constant_features = []
    for feat, vals in all_values_by_feat.items():
        if len(set(vals)) <= 1:
            constant_features.append(feat)

    # -------------------------------------------------------------------------
    # Summary section
    # -------------------------------------------------------------------------
    summary = {
        "total_group_fixtures": len(group_matches),
        "fixtures_full_coverage": full_coverage_count,
        "fixtures_with_any_imputed": any_imputed_count,
        "fixtures_name_resolution_failed": len([e for e in audit_entries if e["status"] == "name_resolution_failed"]),
        "teams_name_resolution_failed": sorted(name_fail_teams),
        "teams_stale_data": sorted(stale_teams),
        "features_with_imputation_count": imputed_freq,
        "constant_features_across_2026": constant_features,
        "stale_cutoff": str(STALE_CUTOFF)[:10],
    }

    audit_output = {
        "summary": summary,
        "fixtures": audit_entries,
    }

    os.makedirs(CACHE_DIR, exist_ok=True)
    audit_path = os.path.join(CACHE_DIR, "feature_audit.json")
    with open(audit_path, "w") as f:
        json.dump(audit_output, f, indent=2, default=str)
    print(f"\nAudit written to: {audit_path}")

    # -------------------------------------------------------------------------
    # D2: Full SHAP/LR contribution dump for two specific matches
    # -------------------------------------------------------------------------
    shap_matches = [
        ("Mexico", "South Africa"),
        ("South Korea", "Czech Republic"),
    ]
    shap_output = {}

    for t1_raw, t2_raw in shap_matches:
        t1_canon, _ = canonicalize(t1_raw, name_map, all_canonicals)
        t2_canon, _ = canonicalize(t2_raw, name_map, all_canonicals)

        if t1_canon not in snapshots or t2_canon not in snapshots:
            print(f"WARNING: Cannot find snapshots for {t1_raw} vs {t2_raw}")
            continue

        snap1 = snapshots[t1_canon]
        snap2 = snapshots[t2_canon]
        X = build_inference_row(snap1, snap2, 2, feat_cols)

        proba = model.predict_proba(X)[0]
        p_away, p_draw, p_home = float(proba[0]), float(proba[1]), float(proba[2])
        pred_label = max([("team1", p_home), ("draw", p_draw), ("team2", p_away)], key=lambda x: x[1])[0]
        pred_class_idx = {"team1": 2, "draw": 1, "team2": 0}[pred_label]

        contributions = compute_full_lr_contributions(expl_model, X, feat_cols)

        raw_values = {}
        imputed = get_imputed_features(X, model, feat_cols)
        for feat in feat_cols:
            v = X[feat].iloc[0]
            raw_values[feat] = None if pd.isna(v) else round(float(v), 6)

        shap_output[f"{t1_raw} vs {t2_raw}"] = {
            "team1": t1_canon,
            "team2": t2_canon,
            "team1_snapshot_date": str(snapshot_dates[t1_canon])[:10],
            "team2_snapshot_date": str(snapshot_dates[t2_canon])[:10],
            "probabilities": {
                "team1Win": round(p_home, 4),
                "draw": round(p_draw, 4),
                "team2Win": round(p_away, 4),
            },
            "predictedOutcome": pred_label,
            "raw_feature_values": raw_values,
            "imputed_features": imputed,
            "lr_contributions_by_class": contributions,
        }

        # Print summary for predicted class
        pred_class_label = {2: "H (home win)", 1: "D (draw)", 0: "A (away win)"}[pred_class_idx]
        class_key = {2: "H", 1: "D", 0: "A"}[pred_class_idx]
        contribs = contributions[class_key]
        sorted_contribs = sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)

        print(f"\n{'='*60}")
        print(f"D2: {t1_raw} vs {t2_raw}")
        print(f"  Canonical: {t1_canon} vs {t2_canon}")
        print(f"  Snapshots: {str(snapshot_dates[t1_canon])[:10]} / {str(snapshot_dates[t2_canon])[:10]}")
        print(f"  Probabilities: team1={p_home:.3f}, draw={p_draw:.3f}, team2={p_away:.3f}")
        print(f"  Predicted: {pred_label} ({pred_class_label})")
        print(f"  Imputed features: {imputed if imputed else 'none'}")
        print(f"\n  Full LR contributions for predicted class '{class_key}':")
        print(f"  {'Feature':<35} {'Contribution':>12}  {'Direction'}")
        print(f"  {'-'*35} {'-'*12}  {'-'*20}")
        for feat, contrib in sorted_contribs:
            direction = f"favors team1 ({t1_raw})" if contrib > 0 else f"favors team2 ({t2_raw})"
            marker = " *** CONSTANT ***" if feat in constant_features else ""
            print(f"  {feat:<35} {contrib:>12.4f}  {direction}{marker}")

    shap_path = os.path.join(CACHE_DIR, "shap_dump.json")
    with open(shap_path, "w") as f:
        json.dump(shap_output, f, indent=2, default=str)
    print(f"\nSHAP dump written to: {shap_path}")

    # -------------------------------------------------------------------------
    # Print D1 human-readable summary
    # -------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("D1 FEATURE COVERAGE AUDIT SUMMARY")
    print(f"{'='*60}")
    print(f"  Total group fixtures:               {summary['total_group_fixtures']}")
    print(f"  Full coverage (0 imputed):          {summary['fixtures_full_coverage']}")
    print(f"  Has any imputed features:           {summary['fixtures_with_any_imputed']}")
    print(f"  Name resolution failures:           {summary['fixtures_name_resolution_failed']}")
    print(f"  Failed teams:                       {summary['teams_name_resolution_failed']}")
    print(f"\n  Teams with stale data (<{str(STALE_CUTOFF)[:10]}):")
    for t in summary["teams_stale_data"]:
        dt = None
        for e in audit_entries:
            if e.get("team1_canonical") == t:
                dt = e.get("team1_snapshot_date"); break
            if e.get("team2_canonical") == t:
                dt = e.get("team2_snapshot_date"); break
        print(f"    {t}: last row = {dt}")
    print(f"\n  Constant features across 2026 fixtures: {constant_features}")
    print(f"\n  Features imputed (NaN → median) across fixtures:")
    for feat, cnt in sorted(imputed_freq.items(), key=lambda x: -x[1]):
        print(f"    {feat:<35} imputed in {cnt}/{len(group_matches)} fixtures")
    if not imputed_freq:
        print("    (none)")


if __name__ == "__main__":
    main()
