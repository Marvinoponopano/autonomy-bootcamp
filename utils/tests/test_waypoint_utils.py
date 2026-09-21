"""
TODO(bootcamper): write the tests for ``src/waypoint_utils.py`` in here.

The example below covers files that parse fine: with and without ``home``,
and files with comments and blank lines in them. The rest is yours:

- Bad data: a file whose top level isn't a mapping, waypoints missing
  ``lat``, ``lon``, or ``alt``, values that aren't numbers, YAML that
  doesn't parse, and a file that isn't there.
- Out of range: latitudes past +/-90 and longitudes past +/-180 get
  rejected.
- Nothing to work with: an empty file, an empty ``waypoints`` list, and
  ``sort_clockwise_sweep`` given a list of 0 or 1 waypoints.
- ``east_north_coordinate_offset_m``: offsets you worked out yourself,
  compared with ``pytest.approx``. Never use ``==`` on meters.
- Ordering: with no ``home``, ``sort_clockwise_sweep`` goes clockwise
  starting from north.
- With a ``home``: the order starts in home's direction instead, and goes
  back to starting at north if home is right on top of the centroid.
- Two waypoints in the same direction: the closer one comes first.
- Parsing gives you frozen ``Coordinate`` objects that can't be changed.

Graded by ``warg run utils grade-tests``: pass on the real code, 90% branch
coverage, and fail on every broken copy in ``grader/mutants/``.
"""

import pytest

from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)
from src.types import Coordinate

# The helper and the test below are given to you.


def write_to_tmp_waypoints_file(tmp_path, text):
    """Write ``text`` to a YAML file and hand back its path.

    ``tmp_path`` is a pytest fixture: a fresh empty directory per test.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


# One test, three files. ``parametrize`` runs the test body once per
# ``(text, expected)`` pair, and ``ids`` names each run so a failure tells you
# which file broke.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
            home: {lat: 1, lon: 2, alt: 3}
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            """
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
              - {lat: 7, lon: 8, alt: 9}
            """,
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            """
            # a lap

            home: {lat: 1, lon: 2, alt: 3}

            waypoints:
              # first leg
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines"],
)
def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected



# tests
def test_parse_waypoints_file_rejects_bad_input(tmp_path):
    bad_cases = [
        "home: 123\nwaypoints: []\n",
        "home: {lat: 1, lon: 2}\nwaypoints: []\n",
        "home: {lat: nope, lon: 2, alt: 3}\nwaypoints: []\n",
        "waypoints:\n  - {lat: 91, lon: 0, alt: 1}\n",
        "waypoints: [not, valid]\n",
        "home: [1, 2, 3]\nwaypoints: []\n",
    ]

    for text in bad_cases:
        path = write_to_tmp_waypoints_file(tmp_path, text)
        with pytest.raises(ValueError):
            parse_waypoints_file(path)

    missing_path = tmp_path / "missing.yaml"
    with pytest.raises(OSError):
        parse_waypoints_file(missing_path)


def test_parse_waypoints_file_empty_file_returns_empty_result(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "")
    assert parse_waypoints_file(path) == (None, [])


def test_parse_waypoints_file_rejects_non_mapping_and_non_list_inputs(tmp_path):
    for text in ["42\n", "[]\n", "- lat: 1\n  lon: 2\n  alt: 3\n", "waypoints: {lat: 1, lon: 2, alt: 3}\n"]:
        path = write_to_tmp_waypoints_file(tmp_path, text)
        with pytest.raises(ValueError):
            parse_waypoints_file(path)

    path = write_to_tmp_waypoints_file(tmp_path, "home: [1, 2, 3]\nwaypoints: 5\n")
    with pytest.raises(ValueError):
        parse_waypoints_file(path)

    invalid_yaml = write_to_tmp_waypoints_file(tmp_path, "home: [1, 2\n")
    with pytest.raises(ValueError):
        parse_waypoints_file(invalid_yaml)


def test_east_north_coordinate_offset_m_basic_cases():
    east, north = east_north_coordinate_offset_m(0.0, 0.0, 0.0, 1.0)
    assert east > 0
    assert north == pytest.approx(0.0, abs=1e-9)

    east, north = east_north_coordinate_offset_m(0.0, 0.0, 1.0, 0.0)
    assert east == pytest.approx(0.0, abs=1e-9)
    assert north > 0

    east, north = east_north_coordinate_offset_m(0.0, 0.0, 0.0, 0.0)
    assert (east, north) == pytest.approx((0.0, 0.0))


def test_sort_clockwise_sweep_starts_from_north_by_default():
    points = [
        Coordinate(1.0, 0.0, 0.0),
        Coordinate(0.0, 1.0, 0.0),
        Coordinate(-1.0, 0.0, 0.0),
        Coordinate(0.0, -1.0, 0.0),
    ]

    ordered = sort_clockwise_sweep(points)
    assert ordered == [
        Coordinate(1.0, 0.0, 0.0),
        Coordinate(0.0, 1.0, 0.0),
        Coordinate(-1.0, 0.0, 0.0),
        Coordinate(0.0, -1.0, 0.0),
    ]


def test_sort_clockwise_sweep_handles_empty_and_singleton_lists():
    assert sort_clockwise_sweep([]) == []
    single = [Coordinate(1.0, 2.0, 3.0)]
    assert sort_clockwise_sweep(single) == single


def test_sort_clockwise_sweep_uses_home_direction_when_home_is_not_centroid():
    points = [
        Coordinate(1.0, 0.0, 0.0),
        Coordinate(0.0, 1.0, 0.0),
        Coordinate(-1.0, 0.0, 0.0),
        Coordinate(0.0, -1.0, 0.0),
    ]
    home = Coordinate(0.0, 1.0, 0.0)

    ordered = sort_clockwise_sweep(points, home=home)
    assert ordered == [
        Coordinate(0.0, 1.0, 0.0),
        Coordinate(-1.0, 0.0, 0.0),
        Coordinate(0.0, -1.0, 0.0),
        Coordinate(1.0, 0.0, 0.0),
    ]


def test_sort_clockwise_sweep_resets_to_north_when_home_is_centroid():
    points = [
        Coordinate(1.0, 0.0, 0.0),
        Coordinate(0.0, 1.0, 0.0),
        Coordinate(-1.0, 0.0, 0.0),
        Coordinate(0.0, -1.0, 0.0),
    ]
    home = Coordinate(0.0, 0.0, 0.0)

    ordered = sort_clockwise_sweep(points, home=home)
    assert ordered == [
        Coordinate(1.0, 0.0, 0.0),
        Coordinate(0.0, 1.0, 0.0),
        Coordinate(-1.0, 0.0, 0.0),
        Coordinate(0.0, -1.0, 0.0),
    ]


def test_sort_clockwise_sweep_uses_farthest_dist_for_same_direction():
    same_direction = [
        Coordinate(0.0, 2.0, 0.0),
        Coordinate(0.0, 1.0, 0.0),
    ]

    assert sort_clockwise_sweep(same_direction) == [
        Coordinate(0.0, 2.0, 0.0),
        Coordinate(0.0, 1.0, 0.0),
    ]


def test_east_north_coordinate_offset_m_uses_radians_and_latitude_scaling():
    east_0, north_0 = east_north_coordinate_offset_m(0.0, 0.0, 0.0, 1.0)
    east_60, north_60 = east_north_coordinate_offset_m(60.0, 0.0, 60.0, 1.0)
    _, north_1 = east_north_coordinate_offset_m(0.0, 0.0, 1.0, 0.0)

    assert east_0 > 0
    assert east_60 > 0
    assert east_60 < east_0
    assert north_0 == pytest.approx(0.0, abs=1e-6)
    assert north_1 == pytest.approx(111195.0802335329, rel=1e-6)
    assert north_60 == pytest.approx(0.0, abs=1e-6)
    assert east_60 == pytest.approx(55597.54011676647, rel=1e-6)


def test_coordinate_is_frozen():
    from dataclasses import FrozenInstanceError

    coord = Coordinate(1.0, 2.0, 3.0)
    with pytest.raises(FrozenInstanceError):
        coord.lat = 99.0
