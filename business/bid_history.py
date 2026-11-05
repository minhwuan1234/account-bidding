"""Bid history operations used by the HTTP layer."""

from __future__ import annotations

from database.bid_store import create_bid as _create_bid
from database.bid_store import get_bid as _get_bid
from database.bid_store import list_bids as _list_bids
from database.bid_store import update_bid as _update_bid


def create_bid(title: str) -> dict:
    return _create_bid(title)


def list_bids() -> list[dict]:
    return _list_bids()


def get_bid(bid_id: str) -> dict | None:
    return _get_bid(bid_id)


def update_bid(bid_id: str, payload: dict) -> dict | None:
    return _update_bid(bid_id, title=payload.get("title", ""),
                       status=payload.get("status", "processing"),
                       documents=payload.get("documents", []), matches=payload.get("matches"),
                       report=payload.get("report"))
