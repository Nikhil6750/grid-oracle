import argparse
import json
import os
import sys

# Optional fastf1 import
try:
    import fastf1
    FASTF1_AVAILABLE = True
except ImportError:
    FASTF1_AVAILABLE = False

FALLBACK_DATA = {
    "FP1": [
        "LEC", "VER", "PIA", "HAM", "ANT", "RUS", "NOR", "GAS", "HAD", "SAI"
    ],
    "SQ": [
        "NOR", "ANT", "PIA", "LEC", "VER", "RUS", "HAM", "COL", "HAD", "GAS"
    ]
}

DRIVER_NAMES = {
    "NOR": "Lando Norris",
    "PIA": "Oscar Piastri",
    "ANT": "Kimi Antonelli",
    "LEC": "Charles Leclerc",
    "VER": "Max Verstappen",
    "RUS": "George Russell",
    "HAM": "Lewis Hamilton",
    "SAI": "Carlos Sainz",
    "GAS": "Pierre Gasly",
    "HAD": "Isack Hadjar",
    "COL": "Franco Colapinto"
}

PRIORS = {
    "ANT": {"season_form": 1, "team_strength": 2},
    "RUS": {"season_form": 1, "team_strength": 2},
    "NOR": {"season_form": 1, "team_strength": 1},
    "PIA": {"season_form": 1, "team_strength": 1},
    "LEC": {"season_form": 1, "team_strength": 2},
    "VER": {"season_form": 1, "team_strength": 2},
    "HAM": {"season_form": 3, "team_strength": 2},
    "SAI": {"season_form": 5, "team_strength": 3},
    "GAS": {"season_form": 5, "team_strength": 4},
    "HAD": {"season_form": 5, "team_strength": 4},
    "COL": {"season_form": 6, "team_strength": 5},
}

# Fixed priority list for tie-breaks
FIXED_PRIORITY = ["NOR", "PIA", "ANT", "LEC", "VER", "RUS", "HAM", "SAI", "GAS", "HAD", "COL"]

# Default rank for drivers not in PRIORS
DEFAULT_PRIOR = {"season_form": 10, "team_strength": 10}
DEFAULT_SESSION_RANK = 15

def get_fastf1_results(session_name):
    if not FASTF1_AVAILABLE:
        return None
    try:
        fastf1.Cache.enable_cache('data_cache')
        session = fastf1.get_session(2026, 4, session_name)
        session.load(telemetry=False, laps=False, weather=False)
        results = session.results
        if results is None or results.empty:
            return None
        return results['Abbreviation'].tolist()
    except Exception as e:
        return None

def main():
    parser = argparse.ArgumentParser(description="Grid Oracle Current Weekend Prediction (Miami 2026)")
    parser.add_argument("--use-fastf1", action="store_true", help="Force attempt to use FastF1")
    parser.add_argument("--fallback-only", action="store_true", help="Only use fallback data")
    parser.add_argument("--top3-only", action="store_true", help="Print only top 3 (default)")
    parser.add_argument("--details", action="store_true", help="Print full details")
    args = parser.parse_args()

    # Make top3-only the default output format unless details is specified
    if not args.details:
        args.top3_only = True

    if FASTF1_AVAILABLE:
        import logging
        fastf1.logger.set_level(logging.CRITICAL)

    sessions_used = []
    sessions_missing = []
    results_data = {}

    # Gather data
    for session_type in ["FP1", "SQ"]:
        data = None
        if not args.fallback_only and FASTF1_AVAILABLE:
            data = get_fastf1_results(session_type)
        
        if data:
            sessions_used.append(f"{session_type} (FastF1)")
            results_data[session_type] = data
        else:
            if session_type in FALLBACK_DATA:
                sessions_used.append(f"{session_type} (Fallback)")
                results_data[session_type] = FALLBACK_DATA[session_type]
            else:
                sessions_missing.append(session_type)
    
    # Also check S, Q just for info
    for session_type in ["S", "Q"]:
        if not args.fallback_only and FASTF1_AVAILABLE:
            data = get_fastf1_results(session_type)
            if data:
                sessions_used.append(f"{session_type} (FastF1)")
                results_data[session_type] = data
            else:
                sessions_missing.append(f"{session_type} (Not available yet)")
        else:
             sessions_missing.append(f"{session_type} (Not checked/Fallback mode)")


    # Calculate heuristic score
    # Find all drivers seen in either FP1 or SQ
    drivers = set()
    for s_data in results_data.values():
        drivers.update(s_data[:10]) # Fallback data only has top 10

    scores = []
    for driver in drivers:
        fp1_data = results_data.get("FP1", [])
        sq_data = results_data.get("SQ", [])

        fp1_rank = fp1_data.index(driver) + 1 if driver in fp1_data else DEFAULT_SESSION_RANK
        sq_rank = sq_data.index(driver) + 1 if driver in sq_data else DEFAULT_SESSION_RANK
        
        prior = PRIORS.get(driver, DEFAULT_PRIOR)
        season_form_rank = prior["season_form"]
        team_strength_rank = prior["team_strength"]

        # Lower score is better
        score = (0.5 * sq_rank) + (0.25 * fp1_rank) + (0.15 * season_form_rank) + (0.10 * team_strength_rank)
        
        # Calculate pseudo probability (inverse of score normalized)
        prob = max(0.01, (20 - score) / 20.0)

        scores.append({
            "driver": driver,
            "score": round(score, 2),
            "fp1": fp1_rank,
            "sq": sq_rank,
            "form": season_form_rank,
            "team": team_strength_rank,
            "prob_raw": prob,
            "priority": FIXED_PRIORITY.index(driver) if driver in FIXED_PRIORITY else 99
        })

    # Sort by score ascending, then by tie-breakers
    # 1. Lower score
    # 2. Lower SQ rank
    # 3. Lower FP1 rank
    # 4. Lower form rank
    # 5. Fixed priority
    scores.sort(key=lambda x: (x["score"], x["sq"], x["fp1"], x["form"], x["priority"]))

    # Normalize probabilities for top 10
    top10 = scores[:10]
    total_prob_raw = sum(x["prob_raw"] for x in top10)
    for i, item in enumerate(top10):
        # Apply an exponential modifier to spread probabilities
        base_share = (item["prob_raw"] / total_prob_raw) ** 1.5
        item["base_share"] = base_share
    
    total_share = sum(x["base_share"] for x in top10)
    for item in top10:
        item["probability"] = round(item["base_share"] / total_share, 4)

    if args.details:
        print("============================================================")
        print("GRID ORACLE — CURRENT WEEKEND TERMINAL PREDICTION")
        print("2026 Miami Grand Prix (Round 4)")
        print("============================================================\n")

        print(f"Sessions used: {', '.join(sessions_used)}")
        print(f"Sessions missing: {', '.join(sessions_missing)}\n")

        winner = top10[0]
        print("Predicted Race Winner Candidate:")
        print(f"1. {winner['driver']}\n")

        print("Predicted Podium:")
        if len(top10) >= 3:
            print(f"P1  {top10[0]['driver']}")
            print(f"P2  {top10[1]['driver']}")
            print(f"P3  {top10[2]['driver']}\n")
        
        print("Podium Probability Ranking:")
        for item in top10[:5]:
            print(f"{item['driver']:<5} {item['probability']*100:.0f}%")
        print()

        print("Projected Top 10:")
        for i, item in enumerate(top10):
            print(f"{i+1:<2}. {item['driver']}")
        print()

        print("Confidence:")
        print("Medium\n")

        print("Warnings:")
        print("- This is not yet generated by the trained Grid Oracle 2026 feature pipeline.")
        print("- Miami 2026 is a sprint weekend, so predictions should update after Sprint, Qualifying, and final weather data.")
        print("- FastF1 fallback heuristic model in use instead of ML engine.\n")

        print("Scoring Table (Lower is better):")
        print(f"{'DRIVER':<8} | {'SCORE':<6} | {'SQ (50%)':<8} | {'FP1 (25%)':<9} | {'FORM (15%)':<10} | {'TEAM (10%)':<10}")
        print("-" * 65)
        for item in scores:
            print(f"{item['driver']:<8} | {item['score']:<6.2f} | {item['sq']:<8} | {item['fp1']:<9} | {item['form']:<10} | {item['team']:<10}")

    else:
        # Default top 3 only output
        print("GRID ORACLE — MIAMI GP 2026 TOP 3 PREDICTION\n")
        if len(top10) >= 3:
            print(f"P1  {top10[0]['driver']} — {DRIVER_NAMES.get(top10[0]['driver'], top10[0]['driver'])}")
            print(f"P2  {top10[1]['driver']} — {DRIVER_NAMES.get(top10[1]['driver'], top10[1]['driver'])}")
            print(f"P3  {top10[2]['driver']} — {DRIVER_NAMES.get(top10[2]['driver'], top10[2]['driver'])}\n")
        
        print("Confidence: Medium")
        
        # Build data used string
        fastf1_used = any("FastF1" in s for s in sessions_used)
        if fastf1_used:
            print("Data used: FP1 + Sprint Qualifying live data")
        else:
            print("Data used: FP1 + Sprint Qualifying fallback")

    # Output JSON
    output_data = {
        "season": 2026,
        "round": 4,
        "stage": "current_weekend",
        "pole_sitter_candidate": top10[0]["driver"] if top10 else None,
        "race_winner_candidate": top10[0]["driver"] if top10 else None,
        "podium_ranking": [{"driver": x["driver"], "probability": x["probability"]} for x in top10[:3]],
        "top10_ranking": [{"driver": x["driver"], "probability": x["probability"]} for x in top10],
        "models_used": {
            "heuristic_engine": "sprint_weekend_v1"
        },
        "warnings": [
            "Not generated by trained 2026 ML pipeline",
            "Heuristic fallback scoring active"
        ],
        "metadata": {
            "sessions_used": sessions_used,
            "sessions_missing": sessions_missing,
            "scores": [{"driver": s["driver"], "score": s["score"]} for s in scores] # Simplified scores for json to avoid excessive data
        }
    }

    out_path = os.path.join("reports", "miami_2026_current_prediction.json")
    os.makedirs("reports", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=2)

    # Only print JSON path if in details mode to keep Top 3 clean
    if args.details:
        print(f"\nSaved detailed prediction to: {out_path}")

if __name__ == "__main__":
    main()
