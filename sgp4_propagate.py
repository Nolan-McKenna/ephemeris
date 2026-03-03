"""
True SGP4 propagator using official Vallado implementation.

Outputs:
- lat (deg)
- lon (deg)
- alt (km)
- x_eci, y_eci, z_eci (km)
"""

from sgp4.api import Satrec, jday
import numpy as np
import math
from datetime import datetime, timezone, timedelta

# Constants
EARTH_RADIUS_KM = 6378.137
MIN_PER_DAY = 1440.0

# ──────────────────────────────────────────────
# TLE PARSE
# ──────────────────────────────────────────────

def parse_tle(line1, line2):
    sat = Satrec.twoline2rv(line1, line2)
    mean_motion = float(line2[52:63])

    return {
        "sat": sat,
        "jd_epoch": sat.jdsatepoch + sat.jdsatepochF,
        'mean_motion': mean_motion
    }

# ──────────────────────────────────────────────
# TIME HELPERS
# ──────────────────────────────────────────────

def jd_from_minutes(jd_epoch, minutes):
    return jd_epoch + (minutes / MIN_PER_DAY)

# GMST (Vallado 2006)
def gmst_from_jd(jd):
    T = (jd - 2451545.0) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * T * T
        - T * T * T / 38710000.0
    )
    return math.radians(gmst % 360.0)

# ──────────────────────────────────────────────
# ECI → ECEF
# ──────────────────────────────────────────────

def eci_to_ecef(x, y, z, jd):
    gmst = gmst_from_jd(jd)
    cos_g = math.cos(gmst)
    sin_g = math.sin(gmst)

    x_e = cos_g * x + sin_g * y
    y_e = -sin_g * x + cos_g * y
    z_e = z
    return x_e, y_e, z_e

# ──────────────────────────────────────────────
# ECEF → Lat/Lon/Alt
# ──────────────────────────────────────────────

def ecef_to_geodetic(x, y, z):
    """Converts ECEF (km) to WGS84 Geodetic (Lat, Lon, Alt)."""
    # WGS84 ellipsoid constants
    a = 6378.137
    f = 1 / 298.257223563
    e2 = 2*f - f**2
    
    lon = math.atan2(y, x)
    r = math.sqrt(x**2 + y**2)
    lat = math.atan2(z, r)
    
    # 3 iterations is enough for sub-millimeter precision
    for _ in range(3):
        sin_lat = math.sin(lat)
        N = a / math.sqrt(1 - e2 * sin_lat**2)
        alt = r / math.cos(lat) - N
        lat = math.atan2(z, r * (1 - e2 * (N / (N + alt))))
        
    return math.degrees(lat), math.degrees(lon), alt

# ──────────────────────────────────────────────
# PROPAGATE SINGLE SAT
# ──────────────────────────────────────────────

def propagate(tle_dict, minutes_from_epoch):
    sat = tle_dict["sat"]
    jd = jd_from_minutes(tle_dict["jd_epoch"], minutes_from_epoch)
    fr = 0.0

    e, r, v = sat.sgp4(jd, fr)
    if e != 0:
        raise RuntimeError(f"SGP4 error code: {e}")

    x_eci, y_eci, z_eci = r

    x_ecef, y_ecef, z_ecef = eci_to_ecef(x_eci, y_eci, z_eci, jd)
    lat, lon, alt = ecef_to_geodetic(x_ecef, y_ecef, z_ecef)

    return lat, lon, alt, x_eci, y_eci, z_eci

# ──────────────────────────────────────────────
# EPOCH ALIGNMENT
# ──────────────────────────────────────────────

def epoch_offset_minutes(tle1, tle2):
    return (tle2["jd_epoch"] - tle1["jd_epoch"]) * MIN_PER_DAY

def propagate_at_wall_time(tle, tle_ref, t_from_ref):
    offset = epoch_offset_minutes(tle_ref, tle)
    return propagate(tle, t_from_ref - offset)

# ──────────────────────────────────────────────
# CONJUNCTION ANALYSIS
# ──────────────────────────────────────────────

def compute_miss_distance(tle1, tle2, t_minutes):
    offset = epoch_offset_minutes(tle1, tle2)

    _, _, _, x1, y1, z1 = propagate(tle1, t_minutes)
    _, _, _, x2, y2, z2 = propagate(tle2, t_minutes - offset)

    return math.sqrt(
        (x1 - x2)**2 +
        (y1 - y2)**2 +
        (z1 - z2)**2
    )

def find_closest_approach(tle1, tle2, duration_minutes=90, step=0.5, start_minutes=0.0):
    min_dist = float("inf")
    min_t = start_minutes
    t = start_minutes
    end_t = start_minutes + duration_minutes

    while t <= end_t:
        d = compute_miss_distance(tle1, tle2, t)
        if d < min_dist:
            min_dist = d
            min_t = t
        t += step

    return min_t, min_dist