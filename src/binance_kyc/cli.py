"""CLI entry point for the Binance KYC Telegram bot."""

from __future__ import annotations

import argparse
import sys

import structlog

from binance_kyc import __version__
from binance_kyc.config import RunMode, get_settings
from binance_kyc.utils.logging import setup_logging

logger = structlog.get_logger()


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and start the bot."""
    parser = argparse.ArgumentParser(
        prog="binance-kyc",
        description="Binance KYC Telegram Bot — conversational identity verification",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── run ───────────────────────────────────────────────────
    run_parser = subparsers.add_parser("run", help="Start the Telegram bot")
    run_parser.add_argument(
        "--token",
        help="Telegram bot token (overrides BINANCE_KYC_TELEGRAM_TOKEN)",
    )
    run_parser.add_argument(
        "--mode",
        choices=["demo", "production"],
        help="Run mode (overrides BINANCE_KYC_MODE)",
    )
    run_parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    # ── validate ──────────────────────────────────────────────
    subparsers.add_parser("validate", help="Validate configuration and exit")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    settings = get_settings()

    # Apply CLI overrides
    if args.command == "run":
        if args.token:
            settings.telegram_token = args.token
        if args.mode:
            settings.mode = RunMode(args.mode)
        if args.log_level:
            settings.log_level = args.log_level

    setup_logging(settings.log_level)

    if args.command == "validate":
        return _cmd_validate(settings)

    if args.command == "run":
        return _cmd_run(settings)

    return 0


def _cmd_validate(settings) -> int:
    """Validate configuration."""
    errors: list[str] = []

    if not settings.telegram_token:
        errors.append("BINANCE_KYC_TELEGRAM_TOKEN is required")

    if settings.mode == RunMode.PRODUCTION:
        if not settings.api_key:
            errors.append("BINANCE_KYC_API_KEY is required in production mode")
        if not settings.api_secret:
            errors.append("BINANCE_KYC_API_SECRET is required in production mode")

    if errors:
        for err in errors:
            logger.error("config_error", message=err)
        return 1

    logger.info(
        "config_valid",
        mode=settings.mode,
        data_dir=str(settings.data_dir),
        log_level=settings.log_level,
    )
    return 0


def _cmd_run(settings) -> int:
    """Start the Telegram bot."""
    if not settings.telegram_token:
        logger.error("missing_token", message="Set BINANCE_KYC_TELEGRAM_TOKEN or use --token")
        return 1

    logger.info(
        "starting_bot",
        mode=settings.mode,
        data_dir=str(settings.data_dir),
    )

    from binance_kyc.handlers.telegram import build_app

    app = build_app(settings)

    if settings.telegram_webhook_url:
        logger.info("webhook_mode", url=settings.telegram_webhook_url)
        # Webhook mode for production deployments
        app.run_webhook(
            listen="0.0.0.0",
            port=8443,
            url_path="webhook",
            webhook_url=settings.telegram_webhook_url,
        )
    else:
        logger.info("polling_mode")
        app.run_polling(drop_pending_updates=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
