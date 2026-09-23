"""CLI for installed or checkout-based synthetic claims workflows."""

import argparse
import json
from pathlib import Path

from .detect import detect_directory
from .generate import generate, validate_clean
from .inject import inject
from .model import write_dataset


def main():
    parser = argparse.ArgumentParser(description="Synthetic claims quality study")
    commands = parser.add_subparsers(dest="command", required=True)
    generate_cmd = commands.add_parser("generate")
    generate_cmd.add_argument("--out", type=Path, required=True)
    generate_cmd.add_argument("--seed", type=int, default=17)
    generate_cmd.add_argument("--scenario", choices=["sparse", "standard", "stress"], default="standard")
    detect_cmd = commands.add_parser("detect")
    detect_cmd.add_argument("--data", type=Path, required=True)
    detect_cmd.add_argument("--out", type=Path, required=True)
    report_cmd = commands.add_parser("report")
    report_cmd.add_argument("--out", type=Path, default=Path("reports"))
    run_cmd = commands.add_parser("run", help="Generate, check, score and review a new synthetic run")
    run_cmd.add_argument("--out", type=Path, required=True)
    run_cmd.add_argument("--seed", type=int, default=17)
    run_cmd.add_argument("--scenario", choices=["sparse", "standard", "stress"], default="standard")
    review_cmd = commands.add_parser("review", help="Create a label-free issue report from saved flags")
    review_cmd.add_argument("--flags", type=Path, required=True)
    review_cmd.add_argument("--out", type=Path, required=True)
    expanded_cmd = commands.add_parser("expanded-report")
    expanded_cmd.add_argument("--out", type=Path, default=Path("reports/expanded"))
    dashboard_cmd = commands.add_parser("dashboard")
    dashboard_cmd.add_argument("--out", type=Path, required=True)
    dashboard_cmd.add_argument("--seed", type=int, default=17)
    extract_cmd = commands.add_parser(
        "tableau-extract", help="Create a local Hyper-backed dashboard candidate; never uploads"
    )
    extract_cmd.add_argument(
        "--data", type=Path, required=True, help="Directory produced by the dashboard command"
    )
    args = parser.parse_args()
    if args.command == "tableau-extract":
        from .tableau_extract import convert_dashboard

        try:
            result = convert_dashboard(args.data)
        except (ValueError, OSError) as error:
            parser.exit(2, str(error) + "\n")
        print(json.dumps(result, sort_keys=True))
        return
    if args.command == "expanded-report":
        from .expanded import build_expanded_report

        build_expanded_report(args.out)
        print("Expanded evaluation written to", args.out)
        return
    if args.command == "dashboard":
        from .dashboard import build_dashboard

        build_dashboard(args.out, args.seed)
        print("Tableau files and reconciled inputs written to", args.out)
        return
    if args.command == "run":
        from .workflow import run

        try:
            destination = run(args.out, args.seed, args.scenario)
        except (ValueError, OSError) as error:
            parser.exit(2, str(error) + "\n")
        print("Verified synthetic run written to", destination)
        return
    if args.command == "review":
        from .workflow import review_text

        text = review_text(json.loads(args.flags.read_text()))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print("Issue review written to", args.out)
        return
    if args.command == "generate":
        clean = generate(args.seed)
        validate_clean(clean)
        dirty, truth = inject(clean, args.seed, args.scenario)
        write_dataset(clean, args.out / "clean")
        write_dataset(dirty, args.out / "dirty")
        (args.out / "ground_truth").mkdir(parents=True, exist_ok=True)
        (args.out / "ground_truth" / "manifest.json").write_text(json.dumps(truth, indent=2) + "\n")
        print("Wrote clean, dirty, and separate ground_truth directories to", args.out)
    elif args.command == "detect":
        flags = detect_directory(args.data)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(flags, indent=2) + "\n")
        print("Wrote", len(flags), "check-level flags to", args.out)
    else:
        from .report import build_report

        build_report(args.out)
        print("Wrote measured reports to", args.out)


if __name__ == "__main__":
    main()
