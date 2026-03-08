from pathlib import Path

from fastapi.responses import FileResponse
from pymongo.errors import ServerSelectionTimeoutError

from app.routers import assets


class _FailingCollection:
    def find_one(self, *_args, **_kwargs):
        raise ServerSelectionTimeoutError("ReplicaSetNoPrimary")


class _FailingMongoDb:
    def __getitem__(self, _name: str):
        return _FailingCollection()


def test_static_asset_falls_back_to_local_file_when_mongo_read_fails(monkeypatch):
    invalidations: list[str] = []

    monkeypatch.setattr(assets, "get_mongo_db", lambda: _FailingMongoDb())
    monkeypatch.setattr(assets, "invalidate_mongo_connection", lambda exc: invalidations.append(str(exc)))

    response = assets.get_static_asset("auth-side-panel-bg")

    assert isinstance(response, FileResponse)
    assert Path(str(response.path)).name == "auth-side-panel-bg.png"
    assert invalidations == ["ReplicaSetNoPrimary"]
