"""Ingestion orchestration: session -> discovery -> extraction -> store."""

from __future__ import annotations

import sqlite3

from grocery_agent.ingest import discovery, extract
from grocery_agent.ingest.browser import (
    ensure_logged_in,
    get_account_name,
    open_account_session,
)
from grocery_agent.store import normalize
from grocery_agent.store.accounts import register_account
from grocery_agent.store.schema import connect

BASE_URL = "https://shengsiong.com.sg/"


def run_ingest(account: str) -> int:
    """Run one ingestion pass for a single named account.

    Returns the number of newly extracted transactions. Per the
    transaction-ingestion spec: incremental (already-captured IDs are
    skipped), and a failure on one transaction never loses the rest.
    """
    conn = connect()
    if getattr(conn, "schema_migrated", False):
        # Normalized tables were rebuilt after a schema migration; restore
        # them from the retained raw captures.
        print("Schema migrated: re-normalizing from raw captures...")
        normalize.renormalize(conn)
    pw, context = open_account_session(account)
    extracted = 0
    failures: list[tuple[str, str]] = []
    try:
        page = context.new_page()
        ensure_logged_in(page)

        # The account identifier is the display name the site shows
        # ("Hi, <name>"), not the local profile label.
        site_name = get_account_name(page)
        if site_name:
            print(f"Authenticated as account '{site_name}' (profile '{account}').")
        else:
            site_name = account
            print(
                f"Could not read the account name from the site; "
                f"falling back to profile label '{account}'."
            )
        try:
            register_account(conn, site_name)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            context.close()
            pw.stop()
            conn.close()
            return 1

        _navigate_to_transactions(page)

        listings = discovery.discover_transactions(page)
        all_listed = [
            {**txn, "txn_type": kind}
            for kind, txns in listings.items()
            for txn in txns
        ]
        print(f"Discovered {len(all_listed)} transactions for account '{site_name}'.")

        for txn in all_listed:
            transaction_id = txn["transaction_id"]
            if normalize.has_transaction(conn, site_name, transaction_id):
                continue
            try:
                raw = extract.extract_transaction_details(
                    page, transaction_id, txn["receipt_url"]
                )
                raw.update(
                    {
                        "purchased_at": txn["date_time"],
                        "txn_type": txn["txn_type"],
                        "store_location": txn["store_location"],
                        "total": txn["total"],
                    }
                )
                normalize.ingest_raw(conn, site_name, raw)
                extracted += 1
                print(f"  captured {transaction_id}")
            except Exception as exc:  # failure isolation per transaction
                failures.append((transaction_id, str(exc)))
                print(f"  FAILED {transaction_id}: {exc}")
    finally:
        conn.close()
        context.close()
        pw.stop()

    if failures:
        print(f"\n{len(failures)} transaction(s) failed; re-run to retry them.")
    print(f"Extraction complete: {extracted} new transaction(s) for '{site_name}'.")
    return 0


def _navigate_to_transactions(page) -> None:
    """Reach the Transactions page via in-app navigation.

    The site is an SPA: /account/order-history only renders after clicking
    the Transactions link on the /account page.
    """
    page.goto(f"{BASE_URL}account", wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass  # SPA may keep polling; proceed after idle-or-timeout
    link = page.locator("a[href='/account/order-history']").first
    link.wait_for(state="visible", timeout=15000)
    link.click()
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass  # SPA may keep polling; proceed after idle-or-timeout
    page.wait_for_timeout(2000)
