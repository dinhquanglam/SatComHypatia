# MIT License
#
# Copyright (c) 2020 Debopam Bhattacherjee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import math

try:
    from . import util
except (ImportError, SystemError):
    import util

# Visualizes paths between endpoints at specific time instances

EARTH_RADIUS = 6378135.0 # WGS72 value; taken from https://geographiclib.sourceforge.io/html/NET/NETGeographicLib_8h_source.html

# CONSTELLATION GENERATION GENERAL CONSTANTS
ECCENTRICITY = 0.0000001  # Circular orbits are zero, but pyephem does not permit 0, so lowest possible value
ARG_OF_PERIGEE_DEGREE = 0.0
PHASE_DIFF = True
EPOCH = "2000-01-01 00:00:00"

# CONSTELLATION SPECIFIC PARAMETERS
# STARLINK 550
NAME = "starlink_550"

################################################################
# The below constants are taken from Starlink's FCC filing as below:
# [1]: https://fcc.report/IBFS/SAT-MOD-20190830-00087
################################################################

MEAN_MOTION_REV_PER_DAY = 15.19  # Altitude ~550 km
ALTITUDE_M = 550000  # Altitude ~550 km
SATELLITE_CONE_RADIUS_M = 940700 # From https://fcc.report/IBFS/SAT-MOD-20181108-00083/1569860.pdf (minimum angle of elevation: 25 deg)
MAX_GSL_LENGTH_M = math.sqrt(math.pow(SATELLITE_CONE_RADIUS_M, 2) + math.pow(ALTITUDE_M, 2))
MAX_ISL_LENGTH_M = 2 * math.sqrt(math.pow(EARTH_RADIUS + ALTITUDE_M, 2) - math.pow(EARTH_RADIUS + 80000, 2)) # ISLs are not allowed to dip below 80 km altitude in order to avoid weather conditions
NUM_ORBS = 72
NUM_SATS_PER_ORB = 22
INCLINATION_DEGREE = 53


# KUIPER 630
"""
NAME = "kuiper_630"

################################################################
# The below constants are taken from Kuiper's FCC filing as below:
# [1]: https://www.itu.int/ITU-R/space/asreceived/Publication/DisplayPublication/8716
################################################################

MEAN_MOTION_REV_PER_DAY = 14.80  # Altitude ~630 km
ALTITUDE_M = 630000  # Altitude ~630 km
SATELLITE_CONE_RADIUS_M = ALTITUDE_M / math.tan(math.radians(30.0))  # Considering an elevation angle of 30 degrees; possible values [1]: 20(min)/30/35/45
MAX_GSL_LENGTH_M = math.sqrt(math.pow(SATELLITE_CONE_RADIUS_M, 2) + math.pow(ALTITUDE_M, 2))
MAX_ISL_LENGTH_M = 2 * math.sqrt(math.pow(EARTH_RADIUS + ALTITUDE_M, 2) - math.pow(EARTH_RADIUS + 80000, 2))  # ISLs are not allowed to dip below 80 km altitude in order to avoid weather conditions
NUM_ORBS = 34
NUM_SATS_PER_ORB = 34
INCLINATION_DEGREE = 51.9
"""

# General files needed to generate visualizations; Do not change for different simulations
topFile = "../static_html/top.html"
bottomFile = "../static_html/bottom.html"
city_detail_file = "../../paper/satellite_networks_state/input_data/ground_stations_cities_sorted_by_estimated_2025_pop_top_1000.basic.txt"

# Time in ms for which visualization will be generated
GEN_TIME=46800  #ms

# Input file; Generated during simulation
# Note the file_name consists of the 2 city IDs being offset by the size of the constellation
# City IDs are available in the city_detail_file.
# If city ID is X (for Paris X = 24) and constellation is Starlink_550 (1584 satellites),
# then offset ID is 1584 + 24 = 1608.
path_file = "../../paper/satgenpy_analysis/data/starlink_550_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls/100ms_for_200s/manual/data/networkx_path_1608_to_1650.txt"

# Output directory for creating visualization html files
OUT_DIR = "../viz_output/"
OUT_HTML_FILE = OUT_DIR + NAME + "_path"

sat_objs = []
city_details = {}
paths_over_time = []


def _read_path_schedule(path_filename):
    """
    Reads path transition events and converts transition time from ns to ms.
    """
    schedule = []
    lines = [line.rstrip('\n') for line in open(path_filename) if line.strip()]
    for line in lines:
        val = line.split(",")
        start_ms = int(round(int(val[0]) / 1000000))
        nodes = [int(x) for x in val[1].split("-")]
        schedule.append((start_ms, nodes))
    schedule.sort(key=lambda x: x[0])
    if not schedule:
        raise ValueError("Path file is empty: " + path_filename)
    return schedule


def _selected_path_nodes(path_schedule, sel_time_ms):
    """
    Returns the active path at a specific millisecond.
    """
    sel_path = path_schedule[0][1]
    for i in range(len(path_schedule)):
        start_ms = path_schedule[i][0]
        start_next_ms = path_schedule[i + 1][0] if i + 1 < len(path_schedule) else 99999999999
        if sel_time_ms >= start_ms and sel_time_ms < start_next_ms:
            sel_path = path_schedule[i][1]
            break
    return sel_path


def _satellite_js_payload():
    """
    Builds per-satellite metadata required for JS-side orbit propagation.
    """
    sat_init = []
    sat_meta = []
    for sat in sat_objs:
        sat["sat_obj"].compute(EPOCH)
        sat_init.append({
            "lon_deg": math.degrees(sat["sat_obj"].sublong),
            "lat_deg": math.degrees(sat["sat_obj"].sublat),
            "alt_m": sat["alt_km"] * 1000
        })

        orb_id = sat["orb_id"]
        orb_sat_id = sat["orb_sat_id"]
        orbit_shift = 0.0
        if PHASE_DIFF and orb_id % 2 == 1:
            orbit_shift = 360.0 / (NUM_SATS_PER_ORB * 2.0)
        mean_anomaly_deg_0 = orbit_shift + (orb_sat_id * 360.0 / NUM_SATS_PER_ORB)
        raan_deg = orb_id * 360.0 / NUM_ORBS

        sat_meta.append({
            "raan_deg": raan_deg,
            "inc_deg": INCLINATION_DEGREE,
            "m0_deg": mean_anomaly_deg_0,
            "mean_motion_rev_per_day": MEAN_MOTION_REV_PER_DAY,
            "alt_m": ALTITUDE_M
        })

    return sat_init, sat_meta


def generate_path_at_time():
    """
    Generates a dynamic end-to-end path visualization:
    - Satellites follow physical orbital propagation over time
    - End-to-end path switches according to networkx_path_*.txt events
    :return: HTML formatted string for visualization
    """
    viz_parts = []
    global paths_over_time
    global OUT_HTML_FILE
    paths_over_time = _read_path_schedule(path_file)
    sel_path = _selected_path_nodes(paths_over_time, GEN_TIME)

    num_sats = NUM_ORBS * NUM_SATS_PER_ORB
    sim_start_ms = min(paths_over_time[0][0], GEN_TIME)
    sim_end_ms = max(paths_over_time[-1][0] + 1000, GEN_TIME + 1000)

    src_gs_id = sel_path[0] - num_sats
    dst_gs_id = sel_path[-1] - num_sats
    OUT_HTML_FILE += "_" + city_details[src_gs_id]["name"] + "_" + str(sel_path[0])
    OUT_HTML_FILE += "_" + city_details[dst_gs_id]["name"] + "_" + str(sel_path[-1])
    OUT_HTML_FILE += "_" + str(GEN_TIME) + ".html"

    sat_init, sat_meta = _satellite_js_payload()

    # Include every ground-station node that appears in any path event.
    gs_nodes_in_schedule = {}
    for _, nodes in paths_over_time:
        for node in nodes:
            if node >= num_sats:
                gid = node - num_sats
                gs_nodes_in_schedule[str(node)] = {
                    "lon_deg": float(city_details[gid]["long_deg"]),
                    "lat_deg": float(city_details[gid]["lat_deg"]),
                    "alt_m": float(city_details[gid]["alt_km"]) * 1000.0
                }

    path_schedule_payload = [{"start_ms": t, "nodes": nodes} for t, nodes in paths_over_time]

    viz_parts.append("const SAT_EPOCH = Cesium.JulianDate.fromIso8601('2000-01-01T00:00:00Z');\n")
    viz_parts.append("function jdFromMs(ms) { return Cesium.JulianDate.addSeconds(SAT_EPOCH, ms / 1000.0, new Cesium.JulianDate()); }\n")
    viz_parts.append("viewer.clock.startTime = jdFromMs(" + str(sim_start_ms) + ");\n")
    viz_parts.append("viewer.clock.currentTime = jdFromMs(" + str(GEN_TIME) + ");\n")
    viz_parts.append("viewer.clock.stopTime = jdFromMs(" + str(sim_end_ms) + ");\n")
    viz_parts.append("viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP;\n")
    viz_parts.append("viewer.clock.multiplier = 60;\n")
    viz_parts.append("if (viewer.timeline) { viewer.timeline.zoomTo(viewer.clock.startTime, viewer.clock.stopTime); }\n")

    viz_parts.append("const NUM_SATS = " + str(num_sats) + ";\n")
    viz_parts.append("const EARTH_RADIUS_M = 6378135.0;\n")
    viz_parts.append("const SAT_INIT = " + json.dumps(sat_init, separators=(",", ":")) + ";\n")
    viz_parts.append("const SAT_META = " + json.dumps(sat_meta, separators=(",", ":")) + ";\n")
    viz_parts.append("const PATH_SCHEDULE = " + json.dumps(path_schedule_payload, separators=(",", ":")) + ";\n")
    viz_parts.append("const GS_NODE_POS = " + json.dumps(gs_nodes_in_schedule, separators=(",", ":")) + ";\n")

    viz_parts.append("""
const _eciScratch = new Cesium.Cartesian3();
function satPositionAtTime(satId, time, result) {
    const meta = SAT_META[satId];
    const elapsedSec = Cesium.JulianDate.secondsDifference(time, SAT_EPOCH);
    const raan = Cesium.Math.toRadians(meta.raan_deg);
    const inc = Cesium.Math.toRadians(meta.inc_deg);
    const meanMotion = meta.mean_motion_rev_per_day * Cesium.Math.TWO_PI / 86400.0;
    const u = Cesium.Math.toRadians(meta.m0_deg) + (meanMotion * elapsedSec);
    const r = EARTH_RADIUS_M + meta.alt_m;

    const cosU = Math.cos(u);
    const sinU = Math.sin(u);
    const cosRaan = Math.cos(raan);
    const sinRaan = Math.sin(raan);
    const cosInc = Math.cos(inc);
    const sinInc = Math.sin(inc);

    _eciScratch.x = r * (cosRaan * cosU - sinRaan * sinU * cosInc);
    _eciScratch.y = r * (sinRaan * cosU + cosRaan * sinU * cosInc);
    _eciScratch.z = r * (sinU * sinInc);

    let m = Cesium.Transforms.computeIcrfToFixedMatrix(time);
    if (!Cesium.defined(m)) {
        m = Cesium.Transforms.computeTemeToPseudoFixedMatrix(time);
    }
    if (Cesium.defined(m)) {
        return Cesium.Matrix3.multiplyByVector(m, _eciScratch, result || new Cesium.Cartesian3());
    }
    return Cesium.Cartesian3.clone(_eciScratch, result || new Cesium.Cartesian3());
}

function activePathNodes(elapsedMs) {
    let sel = PATH_SCHEDULE[0].nodes;
    for (let i = 1; i < PATH_SCHEDULE.length; i++) {
        if (elapsedMs < PATH_SCHEDULE[i].start_ms) {
            break;
        }
        sel = PATH_SCHEDULE[i].nodes;
    }
    return sel;
}

const satEntities = new Array(NUM_SATS);
for (let sid = 0; sid < NUM_SATS; sid++) {
    const init = SAT_INIT[sid];
    const satEntity = viewer.entities.add({
        name: '',
        position: Cesium.Cartesian3.fromDegrees(init.lon_deg, init.lat_deg, init.alt_m),
        ellipsoid: {
            radii: new Cesium.Cartesian3(20000.0, 20000.0, 20000.0),
            material: Cesium.Color.BLACK.withAlpha(1.0)
        }
    });
    satEntity.position = new Cesium.CallbackProperty(function(time, result) {
        return satPositionAtTime(sid, time, result);
    }, false);
    satEntities[sid] = satEntity;
}

Object.keys(GS_NODE_POS).forEach(function(nodeId) {
    const gs = GS_NODE_POS[nodeId];
    viewer.entities.add({
        name: '',
        position: Cesium.Cartesian3.fromDegrees(gs.lon_deg, gs.lat_deg, gs.alt_m),
        ellipsoid: {
            radii: new Cesium.Cartesian3(50000.0, 50000.0, 50000.0),
            material: Cesium.Color.GREEN.withAlpha(1.0)
        }
    });
});

viewer.entities.add({
    name: '',
    polyline: {
        positions: new Cesium.CallbackProperty(function(time, result) {
            const elapsedMs = Cesium.JulianDate.secondsDifference(time, SAT_EPOCH) * 1000.0;
            const nodes = activePathNodes(elapsedMs);
            const positions = [];
            for (let i = 0; i < nodes.length; i++) {
                const nodeId = nodes[i];
                if (nodeId >= NUM_SATS) {
                    const gs = GS_NODE_POS[String(nodeId)];
                    if (gs) {
                        positions.push(Cesium.Cartesian3.fromDegrees(gs.lon_deg, gs.lat_deg, gs.alt_m));
                    }
                } else {
                    positions.push(satPositionAtTime(nodeId, time));
                }
            }
            return positions;
        }, false),
        width: 3.0,
        arcType: Cesium.ArcType.NONE,
        material: new Cesium.PolylineOutlineMaterialProperty({
            color: Cesium.Color.RED.withAlpha(1.0),
            outlineWidth: 0,
            outlineColor: Cesium.Color.BLACK
        })
    }
});
""")

    return "".join(viz_parts)


city_details = util.read_city_details(city_details, city_detail_file)
sat_objs = util.generate_sat_obj_list(
    NUM_ORBS,
    NUM_SATS_PER_ORB,
    EPOCH,
    PHASE_DIFF,
    INCLINATION_DEGREE,
    ECCENTRICITY,
    ARG_OF_PERIGEE_DEGREE,
    MEAN_MOTION_REV_PER_DAY,
    ALTITUDE_M
)
viz_string = generate_path_at_time()
util.write_viz_files(viz_string, topFile, bottomFile, OUT_HTML_FILE)
