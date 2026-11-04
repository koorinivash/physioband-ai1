# Notebooks

Optional space for exploratory analysis of collected recordings (elbow-angle plots, tension traces, feature distributions).
All production logic lives in `src/physioband_ml`, so training scripts and the FastAPI backend share exactly one implementation.
Do not copy pipeline code into notebooks; import it instead:

```python
import sys; sys.path.insert(0, "../src")
from physioband_ml.io import load_sensor_csv
from physioband_ml.segmentation import process_frame
```
