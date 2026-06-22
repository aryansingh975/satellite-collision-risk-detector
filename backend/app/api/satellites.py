"""Satellites router — stub for S1.4 router mounting. Full implementation in S6.1/S6.2/S6.3."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_satellites():
    return []
