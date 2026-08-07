"""Adjustable business constants for the waterjet quoting engine.

Change values here; nothing in geometry.py, materials.py, or costing.py
should hard-code any of these.
"""

# Fraction of a standard sheet assumed usable after nesting losses.
NESTING_UTILIZATION_FACTOR = 0.75

# Standard sheet size, in inches.
SHEET_WIDTH_IN = 48.0
SHEET_HEIGHT_IN = 96.0

# If a piece's largest bounding-box dimension exceeds this, flag a warning
# that the area-based material estimate is unreliable for it.
LARGE_PIECE_DIMENSION_THRESHOLD_IN = 40.0

# Machine time cost, in dollars per hour.
MACHINE_RATE_PER_HOUR = 125.0

# Sheet cost per material, in dollars. Placeholder values -- replace with
# real supplier pricing.
SHEET_COST_BY_MATERIAL = {
    "aluminum": 220.0,
    "mild_steel": 150.0,
    "stainless_steel": 340.0,
}

# Flat labor fees applied per job, in dollars. Placeholder values.
LABOR_FLAT_FEES = {
    "programming": 45.0,
    "setup": 35.0,
    "shipping": 25.0,
}

# Tolerance (inches) used to decide whether two contour endpoints are the
# same point when chaining loose LINE/ARC segments into closed loops.
CHAINING_TOLERANCE_IN = 1e-3

# Maximum deviation (inches) allowed when flattening curves (ARC, CIRCLE,
# SPLINE) into straight-line segments for length/perimeter calculations.
FLATTENING_DISTANCE_IN = 0.01

# Pierce time is not tracked directly in the iGEMS materials export -- it is
# derived from the cutting feed rate as PIERCE_TIME_CALIBRATION_CONSTANT /
# feed_rate_ipm. This starting value is an arbitrary placeholder; calibrate
# it against a real known job before trusting quoted pierce times.
PIERCE_TIME_CALIBRATION_CONSTANT = 100.0
