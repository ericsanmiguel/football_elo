"""CLI entry point for football-elo."""

import argparse
from pathlib import Path

from .config import DATA_DIR, INITIAL_RATING, HOME_ADVANTAGE, OUTPUT_DIR
from .data import download_data, load_all
from .output import (
    plot_top_n_history,
    plot_top_n_history_smooth,
    write_history_csv,
    write_rankings_csv,
    write_rankings_markdown,
)
from .pipeline import EloSystem
from .tournaments import audit_tournament_mapping
from .web_export import export_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="football-elo",
        description="Compute Elo ratings for women's international football teams.",
    )
    sub = parser.add_subparsers(dest="command")

    # run (default)
    run_p = sub.add_parser("run", help="Full pipeline: download, compute, output")
    run_p.add_argument("--force-download", action="store_true")
    run_p.add_argument("--start-date", type=str, default=None)
    run_p.add_argument("--initial-rating", type=float, default=INITIAL_RATING)
    run_p.add_argument("--home-advantage", type=float, default=HOME_ADVANTAGE)
    run_p.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    run_p.add_argument("--top", type=int, default=20)

    # download
    dl_p = sub.add_parser("download", help="Download data only")
    dl_p.add_argument("--force", action="store_true")

    # rankings
    rank_p = sub.add_parser("rankings", help="Show current rankings")
    rank_p.add_argument("--top", type=int, default=30)
    rank_p.add_argument("--start-date", type=str, default=None)

    # audit
    sub.add_parser("audit", help="Show tournament K-factor mapping")

    # export-web
    ew_p = sub.add_parser("export-web", help="Export JSON data for website")
    ew_p.add_argument(
        "--gender", choices=["women", "men", "all"], default="all",
        help="Which dataset to export (default: all)",
    )

    return parser


def cmd_run(args: argparse.Namespace) -> None:
    print("Downloading data...")
    download_data(force=args.force_download)

    print("Loading matches...")
    matches = load_all()
    if args.start_date:
        matches = matches[matches["date"] >= args.start_date]
    print(f"  {len(matches)} matches loaded")

    print("Computing Elo ratings...")
    elo = EloSystem(
        initial_rating=args.initial_rating,
        home_advantage=args.home_advantage,
    )
    elo.process_all(matches)

    rankings = elo.get_current_rankings()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    write_rankings_csv(rankings, out / "current_rankings.csv")
    write_rankings_markdown(rankings, out / "current_rankings.md")
    write_history_csv(elo, out / "full_history.csv")
    print(f"  Wrote rankings and history to {out}/")

    print(f"Plotting top {args.top} teams...")
    plot_top_n_history(elo, args.top, out / "top_teams_history.png")
    plot_top_n_history_smooth(elo, args.top, out / "top_teams_history_smooth.png")
    print(f"  Wrote charts to {out}/")

    print(f"\nTop {args.top} Women's International Football Elo Ratings:")
    print(rankings.head(args.top).to_string())


def cmd_download(args: argparse.Namespace) -> None:
    download_data(force=args.force)
    print("Data downloaded.")


def cmd_rankings(args: argparse.Namespace) -> None:
    matches = load_all()
    if args.start_date:
        matches = matches[matches["date"] >= args.start_date]
    elo = EloSystem()
    elo.process_all(matches)
    rankings = elo.get_current_rankings()
    print(rankings.head(args.top).to_string())


def cmd_audit(_args: argparse.Namespace) -> None:
    matches = load_all()
    audit = audit_tournament_mapping(matches)
    print(audit.to_string(index=False))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None or args.command == "run":
        if args.command is None:
            # Apply defaults for run command
            args.force_download = False
            args.start_date = None
            args.initial_rating = INITIAL_RATING
            args.home_advantage = HOME_ADVANTAGE
            args.output_dir = OUTPUT_DIR
            args.top = 20
        cmd_run(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "rankings":
        cmd_rankings(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "export-web":
        cmd_export_web(args)


def _export_gender(gender: str) -> None:
    """Download, compute, and export for a single gender."""
    print(f"\n=== {gender.upper()} ===")
    print("Downloading data...")
    download_data(gender=gender, force=True)
    print("Loading matches...")
    matches = load_all(gender=gender)
    print(f"  {len(matches)} matches loaded")
    print("Computing Elo ratings...")
    elo = EloSystem()
    elo.process_all(matches)
    print("Exporting JSON for website...")
    export_all(elo, gender=gender)


def cmd_export_web(args: argparse.Namespace) -> None:
    genders = ["women", "men"] if args.gender == "all" else [args.gender]
    for g in genders:
        _export_gender(g)
    print("\nDone.")


if __name__ == "__main__":
    main()
