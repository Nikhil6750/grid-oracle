"""Audit Phase 2 ingested data to detect coverage gaps before feature building."""
import sys
import argparse
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.utils.paths import PROCESSED_DATA_DIR


def audit(start_year: int, end_year: int):
    sessions_dir = PROCESSED_DATA_DIR / "sessions"
    if not sessions_dir.exists():
        print(f"[ERROR] Sessions directory not found: {sessions_dir}")
        return

    print("=" * 60)
    print("PHASE 2 DATA AUDIT")
    print("=" * 60)

    all_seasons = sorted([
        d for d in sessions_dir.iterdir()
        if d.is_dir() and d.name.startswith("season=")
    ], key=lambda d: int(d.name.split("=")[1]))

    found_seasons = []
    missing_seasons = []
    season_details = {}

    for year in range(start_year, end_year + 1):
        season_dir = sessions_dir / f"season={year}"
        if not season_dir.exists():
            missing_seasons.append(year)
            print(f"\n[MISSING] Season {year}: directory does not exist")
            continue

        found_seasons.append(year)
        rounds = sorted([
            d for d in season_dir.iterdir()
            if d.is_dir() and d.name.startswith("round=")
        ], key=lambda d: int(d.name.split("=")[1]))

        season_info = {
            "rounds": len(rounds),
            "q_results_count": 0,
            "r_results_count": 0,
            "q_laps_count": 0,
            "r_laps_count": 0,
            "incomplete_events": [],
            "complete_events": [],
        }

        for rnd_dir in rounds:
            round_num = int(rnd_dir.name.split("=")[1])
            q_results = rnd_dir / "Q_results.parquet"
            r_results = rnd_dir / "R_results.parquet"
            q_laps = rnd_dir / "Q_laps.parquet"
            r_laps = rnd_dir / "R_laps.parquet"
            manifest = rnd_dir / "event_manifest.json"

            event_name = f"Round {round_num}"
            if manifest.exists():
                try:
                    with open(manifest) as f:
                        m = json.load(f)
                    event_name = m.get("event_name", event_name)
                except Exception:
                    pass

            has_q = q_results.exists()
            has_r = r_results.exists()
            has_ql = q_laps.exists()
            has_rl = r_laps.exists()

            if has_q:
                season_info["q_results_count"] += 1
            if has_r:
                season_info["r_results_count"] += 1
            if has_ql:
                season_info["q_laps_count"] += 1
            if has_rl:
                season_info["r_laps_count"] += 1

            if not has_q or not has_r:
                reason_parts = []
                if not has_q:
                    reason_parts.append("Q_results.parquet missing")
                if not has_r:
                    reason_parts.append("R_results.parquet missing")
                season_info["incomplete_events"].append({
                    "round": round_num,
                    "event_name": event_name,
                    "reason": "; ".join(reason_parts),
                })
            else:
                season_info["complete_events"].append({
                    "round": round_num,
                    "event_name": event_name,
                })

        season_details[year] = season_info

    # Print report
    print(f"\nSeasons found in processed data: {found_seasons}")
    print(f"Seasons missing entirely:        {missing_seasons}")

    for year, info in season_details.items():
        print(f"\n--- Season {year} ---")
        print(f"  Rounds:         {info['rounds']}")
        print(f"  Q_results:      {info['q_results_count']}/{info['rounds']}")
        print(f"  R_results:      {info['r_results_count']}/{info['rounds']}")
        print(f"  Q_laps:         {info['q_laps_count']}/{info['rounds']}")
        print(f"  R_laps:         {info['r_laps_count']}/{info['rounds']}")
        print(f"  Complete events: {len(info['complete_events'])}")
        print(f"  Incomplete events: {len(info['incomplete_events'])}")

        if info["incomplete_events"]:
            for ev in info["incomplete_events"]:
                print(f"    Round {ev['round']:02d} ({ev['event_name']}): {ev['reason']}")

    # Coverage summary
    print("\n" + "=" * 60)
    print("COVERAGE SUMMARY")
    print("=" * 60)
    usable = [y for y, info in season_details.items() if info["r_results_count"] > 0]
    unusable = [y for y in range(start_year, end_year + 1) if y not in usable]
    print(f"Seasons with usable Q/R data: {usable}")
    print(f"Seasons missing usable Q/R:   {unusable}")
    if unusable:
        print("\n[WARNING] The following seasons need Q/R ingestion before features can be built:")
        for y in unusable:
            print(f"  - {y}")


def main():
    parser = argparse.ArgumentParser(description="Audit Phase 2 data coverage")
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    args = parser.parse_args()
    audit(args.start_year, args.end_year)


if __name__ == "__main__":
    main()
