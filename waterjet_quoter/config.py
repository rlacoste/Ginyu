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

# Base machine time cost, in dollars per hour, for materials with no
# machine_rate_multiplier override in the material_prices table (or a
# multiplier of 1.0). The effective rate is this × that multiplier -- see
# waterjet_quoter.material_prices.
MACHINE_RATE_PER_HOUR = 125.0

# Material density, in kg/m^3, sourced from the iGEMS materials export
# (*Density* column) -- constant per material name, doesn't vary by
# grade/thickness. Used with material_prices.price_per_lb to price by
# weight: weight_lb = net_area_in2 * thickness_in * density_lb_per_in3.
#
# DATA QUALITY WARNING: about a third of these values are almost certainly
# unconfigured iGEMS defaults, not real densities -- e.g. 20 materials
# (Bronze, Carbon fiber, Delrin, Fiberglass, PEEK, PVC, Polypropylene,
# Wood, ...) share the exact value 7800.04 (Mild Steel's density), and
# Dyneema/Plywood share Aluminium's 2700.01. Real density for wood is
# ~500-800, PVC ~1400, PEEK ~1320, Polypropylene ~905 -- none of those are
# 7800. Verify/correct any material below before trusting its weight-based
# price; the values for the metals this shop actually cuts most
# (Aluminium, Mild Steel, Stainless Steel, Copper, Titanium) look
# physically plausible as-is.
DENSITY_KG_PER_M3 = {
    "Acetal": 1393.61,
    "Acrylic": 1185.37,
    "Alu shim stock": 2700.01,
    "Aluminium": 2700.01,
    "Aluminium_AEREM": 2700.01,
    "Alusion Large Cell": 2700.01,
    "Alusion Medium Cell": 2700.01,
    "Black Granite": 2650.01,
    "Board Promutuel": 8450.04,
    "Brass": 8450.04,
    "Bronze": 7800.04,
    "Carbon fiber": 7800.04,
    "Ceramic Tile": 2800.01,
    "Copper": 8900.04,
    "Delrin": 7800.04,
    "Dyneema": 2700.01,
    "Fabreeka TIM": 7800.04,
    "Ferrite": 7800.04,
    "Fiberglass": 7800.04,
    "GPO-3l Rouge WR TRANSFO": 7800.04,
    "Glass": 2600.01,
    "Glastic": 2650.01,
    "Granite": 2800.01,
    "Graphite": 2050.01,
    "HDPC": 7800.04,
    "HDPE": 970.0,
    "Hardox TATA": 7800.04,
    "Inconel": 900.0,
    "Kydex": 927.47,
    "LDPE": 7800.04,
    "Marble": 2650.01,
    "Matériel Rouge Metal Sigma": 7800.04,
    "Mild Steel": 7800.04,
    "Mild Steel AEREM": 7800.04,
    "NEOPRENE2PLY": 1368.12,
    "Nickel Alloy (Magnetic Shield)": 8550.04,
    "Nylon": 1150.13,
    "PEEK": 7800.04,
    "PET (Water only)": 2600.01,
    "PHENOLIQUE": 7800.04,
    "PVC": 7800.04,
    "Plywood": 2700.01,
    "Polycarbonate (Lexan)": 1199.94,
    "Polypropylene": 7800.04,
    "Roc": 2800.01,
    "Rubber": 1230.06,
    "Rubber (brittle)": 80.09,
    "SBR Rubber": 7800.04,
    "Silcatec": 1402.74,
    "Silicon": 80.09,
    "Spring Steel": 8550.04,
    "Stainless Steel": 7999.62,
    "TEFLON": 2199.98,
    "Tapis de vache": 80.09,
    "Titanium": 4500.02,
    "Tool Steel": 8550.04,
    "Tungsten": 8550.04,
    "UHMW": 927.47,
    "Ultratane Bleu Water Only": 1121.29,
    "Urethane AWJ": 7800.04,
    "Wood": 7800.04,
    "Wood- (laminé brittle)": 7800.04,
    "Wood- Hardwood - IPE - Maple": 7800.04,
}

# Markup applied on top of raw weight-based material cost (shipping, kerf/
# edge-margin loss beyond net part area, handling). Placeholder -- tune
# against real invoices. 1.15 = +15%.
MATERIAL_COST_ADJUSTMENT_FACTOR = 1.15

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
