#!/usr/bin/env python3
"""ScribeBox entry point."""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="ScribeBox - Live Transcription Appliance")
    parser.add_argument("--benchmark", action="store_true", help="Run hardware benchmark")
    parser.add_argument("--preferences", action="store_true", help="Open preferences only")
    parser.add_argument("--models-dir", default=None, help="Path to whisper models directory")
    parser.add_argument("--data-dir", default=None, help="Path to data/save directory")
    args = parser.parse_args()

    if args.benchmark:
        from scribebox.benchmark import run_benchmark_cli
        run_benchmark_cli(models_dir=args.models_dir)
        return

    from scribebox.app import ScribeBoxApp
    app = ScribeBoxApp(
        models_dir=args.models_dir,
        data_dir=args.data_dir,
        open_preferences=args.preferences,
    )
    app.run()

if __name__ == "__main__":
    main()
