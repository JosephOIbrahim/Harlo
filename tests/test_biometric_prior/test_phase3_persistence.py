"""Phase 3 — persistence: buffer (kind=biometric_prior, organic, date-idempotent)
+ /cognitive/biometrics USD prim (time-sampled by date), excluded from behavioral
feature windows.
"""

from __future__ import annotations

import json

import pytest

from harlo.biometric_prior.persistence import PRIM_PATH, BufferUsdStore, date_timecode
from harlo.biometric_prior.schema import BiometricPrior
from harlo.engine.observation_buffer import ObservationBuffer
from harlo.engine.schemas import CognitiveObservation


def _prior(date, sleep=330, source="manual"):
    return BiometricPrior(
        captured_at=f"{date}T07:00:00", sleep_minutes=sleep, source=source
    )


@pytest.fixture
def stage():
    from harlo.engine.cognitive_stage import CognitiveStage

    return CognitiveStage(in_memory=True)


def test_buffer_stores_kind_and_excludes_from_sample():
    buf = ObservationBuffer(":memory:")
    # one normal behavioral observation (kind NULL) ...
    buf.add(CognitiveObservation(session_id="s"), partition="organic", surprise_score=0.9)
    # ... and a biometric_prior (kind='biometric_prior')
    buf.add_biometric_prior(_prior("2026-06-10").model_dump_json(), "2026-06-10")

    sampled = buf.sample(n=100)
    # sample() must NOT return the biometric row (and must not crash parsing it
    # as a CognitiveObservation).
    assert all(b.obs_id != "bio-2026-06-10" for b in sampled)
    assert len(sampled) == 1  # only the behavioral observation


def test_buffer_date_idempotent():
    buf = ObservationBuffer(":memory:")
    _id1, created1 = buf.add_biometric_prior(_prior("2026-06-10", sleep=330).model_dump_json(), "2026-06-10")
    _id2, created2 = buf.add_biometric_prior(_prior("2026-06-10", sleep=400).model_dump_json(), "2026-06-10")
    assert created1 is True and created2 is False
    # one row for the date, holding the UPDATED value
    rows = buf.recent_biometric_prior_jsons(50)
    assert len(rows) == 1
    assert json.loads(rows[0])["sleep_minutes"] == 400


def test_usd_prim_time_sampled_and_idempotent(stage):
    buf = ObservationBuffer(":memory:")
    store = BufferUsdStore(buf, stage)

    assert store.upsert(_prior("2026-06-10", sleep=330)) is True   # create
    assert store.upsert(_prior("2026-06-10", sleep=400)) is False  # same-day update

    usda = stage.get_usda_text()
    assert "biometrics" in usda  # /cognitive/biometrics authored
    # The same-day re-POST overwrote the same date time code (not appended):
    data = stage.read(PRIM_PATH, date_timecode("2026-06-10"))
    assert data["sleep_minutes"] == 400
    # only one time sample exists for that prim's data attr
    keys = [k for (p, k) in stage.keys() if p == PRIM_PATH]
    assert keys == [date_timecode("2026-06-10")]


def test_read_helpers(stage):
    buf = ObservationBuffer(":memory:")
    store = BufferUsdStore(buf, stage)
    store.upsert(_prior("2026-06-09", sleep=300))
    store.upsert(_prior("2026-06-10", sleep=450))

    today = store.today_prior("2026-06-10")
    assert today is not None and today.sleep_minutes == 450
    assert store.today_prior("2026-01-01") is None
    recent = store.recent_priors(14)
    assert [p.sleep_minutes for p in recent] == [450, 300]  # newest first
