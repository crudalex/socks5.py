import asyncio
import logging
import argparse
from socks5.server import run_proxy_server

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="SOCKS5 Proxy Server")
    parser.add_argument(
        "--address", default="0.0.0.0", help="Listening address (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port", type=int, default=1080, help="Port number (default: 1080)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout value in seconds (default: 30)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (default: False)",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
    )
    asyncio.run(run_proxy_server(args.address, args.port, args.timeout))
