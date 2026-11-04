"""CSV and API-payload conversion helpers.

CSV format (one row per sample, see ml/data/README.md):
    participant_id, session_id, exercise_id, label, is_synthetic, timestamp_ms,
    ua_ax, ua_ay, ua_az, ua_gx, ua_gy, ua_gz,
    fa_ax, fa_ay, fa_az, fa_gx, fa_gy, fa_gz, force_n
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from physioband_ml.config import FOREARM_CHANNELS, SENSOR_CHANNELS, TIMESTAMP_COLUMN, UPPER_ARM_CHANNELS


def load_sensor_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_sensor_folder(folder: str | Path) -> pd.DataFrame:
    files = sorted(Path(folder).glob("**/*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {folder}")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def samples_to_frame(samples: Iterable[Mapping]) -> pd.DataFrame:
    """Convert API samples ``{timestamp_ms, ua[6], fa[6], force_n}`` to a DataFrame."""
    rows = []
    for s in samples:
        ua = list(s["ua"])
        fa = list(s["fa"])
        row = {TIMESTAMP_COLUMN: s["timestamp_ms"], "force_n": s.get("force_n")}
        row.update(dict(zip(UPPER_ARM_CHANNELS, ua)))
        row.update(dict(zip(FOREARM_CHANNELS, fa)))
        rows.append(row)
    return pd.DataFrame(rows, columns=[TIMESTAMP_COLUMN, *SENSOR_CHANNELS])
