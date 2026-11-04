"""Record a labelled set of real repetitions from the ESP32 over USB serial.

Workflow for each volunteer:
  1. Flash the firmware, connect the ESP32 by USB, close the Arduino Serial Monitor.
  2. Run, for example:
        python scripts/collect_data.py --port COM5 --participant P01 --label correct --reps 10
  3. Press Enter, perform the requested repetitions with the requested quality,
     then press Ctrl+C to stop. One CSV file is written per recorded set into
     data/raw/<participant>/.

The firmware streams CSV lines when it receives the serial command ``csv on``:
    D,<timestamp_ms>,<ua_ax..ua_gz>,<fa_ax..fa_gz>,<force_n>,<status>
"""
import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from _bootstrap import ML_ROOT

from physioband_ml.config import QUALITY_LABELS, SENSOR_CHANNELS, TIMESTAMP_COLUMN

HEADER = ["participant_id", "session_id", "exercise_id", "label", "is_synthetic", TIMESTAMP_COLUMN, *SENSOR_CHANNELS]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", required=True, help="serial port, e.g. COM5")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--participant", required=True, help="anonymous volunteer ID, e.g. P01")
    parser.add_argument("--label", required=True, choices=QUALITY_LABELS)
    parser.add_argument("--exercise", default="biceps_curl")
    parser.add_argument("--reps", type=int, default=10, help="number of reps the volunteer is asked to do")
    parser.add_argument("--out-dir", default=str(ML_ROOT / "data" / "raw"))
    args = parser.parse_args()

    try:
        import serial  # pyserial
    except ImportError:
        sys.exit("pyserial is required: pip install pyserial")

    session_id = f"{args.participant}-{args.label}-{datetime.now():%Y%m%d-%H%M%S}"
    out = Path(args.out_dir) / args.participant / f"{session_id}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        time.sleep(2.0)  # ESP32 resets when the port opens
        ser.reset_input_buffer()
        input(f"Ask {args.participant} to perform {args.reps} '{args.label}' reps. Press Enter to start recording...")
        ser.write(b"csv on\n")
        rows = 0
        print("Recording... press Ctrl+C when the set is finished.")
        with out.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(HEADER)
            try:
                while True:
                    line = ser.readline().decode("ascii", errors="ignore").strip()
                    if not line.startswith("D,"):
                        if line:
                            print(f"  [device] {line}")
                        continue
                    parts = line.split(",")
                    if len(parts) != 16:
                        continue
                    status = int(parts[15])
                    if status & 0b111 != 0b111:
                        print(f"  warning: sensor status {status:#05b} (a sensor is not reporting)")
                    writer.writerow([args.participant, session_id, args.exercise, args.label, False, *parts[1:15]])
                    rows += 1
                    if rows % 250 == 0:
                        print(f"  {rows} samples")
            except KeyboardInterrupt:
                pass
            finally:
                ser.write(b"csv off\n")
    print(f"Saved {rows} samples to {out}")


if __name__ == "__main__":
    main()
