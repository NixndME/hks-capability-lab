from fastapi import APIRouter, HTTPException

from .. import definitions

router = APIRouter()


@router.get("/api/tests")
def list_tests():
    return {
        "count": len(definitions.load_all()),
        "summary": definitions.summary_counts(),
        "categories": definitions.by_category(),
    }


@router.get("/api/tests/{test_id}")
def get_test(test_id: str):
    for entry in definitions.load_all():
        if entry.get("id") == test_id:
            return entry
    raise HTTPException(status_code=404, detail=f"test definition '{test_id}' not found")
