import argparse
import os
import sys
from dataclasses import dataclass

VALID_LOG_LEVELS = {"debug", "info", "warn", "error"}


@dataclass
class Config:
    data_dir: str
    log_level: str
    port: int
    version: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="movies-api",
        description="Movies API — read-only catalog service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variables (lower precedence than flags):\n"
            "  MOVIES_DATA_DIR    Where data files are mounted\n"
            "  MOVIES_LOG_LEVEL   Minimum log level\n"
            "  MOVIES_PORT        HTTP listen port\n"
        ),
    )
    parser.add_argument(
        "--movies-data-dir",
        default=None,
        metavar="PATH",
        help="Where data files are mounted [env: MOVIES_DATA_DIR] [default: /data]",
    )
    parser.add_argument(
        "--movies-log-level",
        default=None,
        metavar="LEVEL",
        help="Minimum log level: debug|info|warn|error [env: MOVIES_LOG_LEVEL] [default: info]",
    )
    parser.add_argument(
        "--movies-port",
        default=None,
        type=int,
        metavar="PORT",
        help="HTTP listen port [env: MOVIES_PORT] [default: 8080]",
    )
    return parser


def parse_config(args=None) -> Config:
    parser = _build_parser()
    parsed, unknown = parser.parse_known_args(args)

    if unknown:
        print(f"Unknown flags: {' '.join(unknown)}", file=sys.stderr)
        sys.exit(1)

    data_dir = parsed.movies_data_dir or os.environ.get("MOVIES_DATA_DIR", "/data")
    log_level = parsed.movies_log_level or os.environ.get("MOVIES_LOG_LEVEL", "info")
    port_env = os.environ.get("MOVIES_PORT", "8080")
    port = parsed.movies_port if parsed.movies_port is not None else int(port_env)
    version = os.environ.get("MOVIES_VERSION", "1.0.0")

    if log_level not in VALID_LOG_LEVELS:
        print(
            f"Invalid log level '{log_level}': must be one of {sorted(VALID_LOG_LEVELS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not (1 <= port <= 65535):
        print(f"Invalid port '{port}': must be 1–65535", file=sys.stderr)
        sys.exit(1)

    return Config(data_dir=data_dir, log_level=log_level, port=port, version=version)
