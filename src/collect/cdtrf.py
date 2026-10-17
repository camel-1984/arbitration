import argparse
import gzip
import json
import logging
import random
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import date
from pathlib import Path

import httpx

BASE_URL = "https://torgi.cdtrf.ru"
RAW_DIR = Path("data/raw/cdtrf")
LOG_PATH = Path("logs/collect_cdtrf.log")
FAILED_PATH = RAW_DIR / "failed_cards.txt"
PASSENGER_CATEGORY = 1
FULL_PAGE_SIZE = 500
EXTRA_PAGES_AFTER_SINCE = 6
USER_AGENT = "itmo-ml-student-project (bankruptcy auctions research)"
DELAY_RANGE = (0.5, 1.0)
BACKOFF = [10, 30, 60, 120]
MAX_CONSECUTIVE_FAILURES = 20

log = logging.getLogger("collect_cdtrf")


class SiteUnavailable(Exception):
    pass


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.FileHandler(LOG_PATH), logging.StreamHandler()):
        handler.setFormatter(formatter)
        log.addHandler(handler)
    log.setLevel(logging.INFO)


def polite_get(client: httpx.Client, url: str, params: dict | None = None) -> httpx.Response | None:
    for attempt, pause in enumerate([0, *BACKOFF]):
        time.sleep(pause or random.uniform(*DELAY_RANGE))
        try:
            response = client.get(url, params=params)
        except httpx.HTTPError as error:
            log.warning("attempt %d %s: %s", attempt + 1, url, error)
            continue
        if response.status_code == 404:
            return None
        if not response.is_success:
            log.warning("attempt %d %s: HTTP %d", attempt + 1, url, response.status_code)
            continue
        return response
    raise SiteUnavailable(url)


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def fetch_list(client: httpx.Client, page: int, page_size: int, sold_only: bool = True) -> dict:
    path = RAW_DIR / ("list" if sold_only else "list_all") / f"cat{PASSENGER_CATEGORY}_size{page_size}_page{page}.json"
    if path.exists():
        return json.loads(path.read_text())
    params = {"Categories": PASSENGER_CATEGORY, "PageSize": page_size, "PageNum": page}
    if sold_only:
        params["SignContract"] = "true"
    response = polite_get(client, f"{BASE_URL}/api/Trade/trades", params)
    if response is None:
        raise SiteUnavailable(f"list page {page}")
    data = response.json()
    write_atomic(path, json.dumps(data, ensure_ascii=False).encode())
    return data


def card_exists(trade_id: int, cards: Path = RAW_DIR / "cards") -> bool:
    return (cards / f"{trade_id}.html.gz").exists() or (cards / f"{trade_id}.html").exists()


def fetch_card(client: httpx.Client, trade_id: int, cards: Path = RAW_DIR / "cards") -> bool:
    response = polite_get(client, f"{BASE_URL}/trades/{trade_id}")
    if response is None:
        log.warning("trade %d: 404", trade_id)
        return False
    write_atomic(cards / f"{trade_id}.html.gz", gzip.compress(response.content))
    return True


def is_passenger_only(item: dict) -> bool:
    return item["categories"].strip(",") == str(PASSENGER_CATEGORY)


def iter_full(client: httpx.Client, since: date):
    page, last_page = 1, None
    while last_page is None or page <= last_page:
        items = fetch_list(client, page, FULL_PAGE_SIZE)["items"]
        if not items:
            return
        for item in items:
            if date.fromisoformat(item["requestTimeBegin"][:10]) < since:
                last_page = last_page or page + EXTRA_PAGES_AFTER_SINCE
            elif is_passenger_only(item):
                yield item["tradeId"]
        page += 1


def collect_list_all(client: httpx.Client, since: date) -> None:
    page, last_page = 1, None
    while last_page is None or page <= last_page:
        items = fetch_list(client, page, FULL_PAGE_SIZE, sold_only=False)["items"]
        if not items:
            break
        if last_page is None and any(date.fromisoformat(item["requestTimeBegin"][:10]) < since for item in items):
            last_page = page + EXTRA_PAGES_AFTER_SINCE
        log.info("list_all page %d", page)
        page += 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=date.fromisoformat, help="all sold lots from this date")
    parser.add_argument("--ids", type=Path, help="file with tradeIds (one per line) instead of the sold catalog")
    parser.add_argument("--cards-dir", type=Path, default=RAW_DIR / "cards", help="where to save cards")
    parser.add_argument("--limit", type=int, default=2500, help="max cards to download in this run")
    parser.add_argument("--workers", type=int, default=3, help="parallel requests")
    parser.add_argument("--max-minutes", type=float, default=60, help="stop this run after N minutes")
    parser.add_argument("--list-all", action="store_true", help="only catalog pages of trades with any status, no cards")
    args = parser.parse_args()
    setup_logging()
    if args.list_all:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60) as client:
            collect_list_all(client, args.since)
        return

    downloaded = skipped = failures = 0
    deadline = time.monotonic() + args.max_minutes * 60
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as client, ThreadPoolExecutor(args.workers) as pool:
        trade_ids = [int(line) for line in args.ids.read_text().split()] if args.ids else iter_full(client, args.since)
        args.cards_dir.mkdir(parents=True, exist_ok=True)
        log.info("start: since=%s limit=%d max_minutes=%s workers=%d", args.since, args.limit, args.max_minutes, args.workers)
        pending = {}
        stop = False
        try:
            for trade_id in trade_ids:
                if card_exists(trade_id, args.cards_dir):
                    skipped += 1
                    continue
                pending[pool.submit(fetch_card, client, trade_id, args.cards_dir)] = trade_id
                while len(pending) >= args.workers * 2 or (stop and pending):
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        done_id = pending.pop(future)
                        try:
                            downloaded += future.result()
                            failures = 0
                        except SiteUnavailable:
                            failures += 1
                            with FAILED_PATH.open("a") as f:
                                f.write(f"{done_id}\n")
                            log.error("trade %d failed after retries (%d in a row)", done_id, failures)
                        if downloaded and downloaded % 100 == 0:
                            log.info("downloaded %d, skipped %d", downloaded, skipped)
                    if failures >= MAX_CONSECUTIVE_FAILURES:
                        log.error("too many failures in a row, stopping")
                        stop = True
                    if downloaded >= args.limit or time.monotonic() > deadline:
                        stop = True
                if stop:
                    break
        except SiteUnavailable as error:
            log.error("catalog unavailable: %s", error)
        for future in pending:
            try:
                downloaded += future.result()
            except SiteUnavailable:
                pass
    log.info("done: downloaded %d, already had %d", downloaded, skipped)


if __name__ == "__main__":
    main()
