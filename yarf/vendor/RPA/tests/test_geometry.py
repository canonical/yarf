import pytest

from yarf.vendor.RPA.core.geometry import Point, Region, to_point, to_region


class TestConversions:
    @pytest.mark.parametrize("obj", ["1,2", (1, 2), [1.0, 2.9], Point(1, 2)])
    def test_to_point(self, obj):
        """
        Test that supported inputs are converted to a Point.
        """
        assert to_point(obj) == Point(1, 2)

    @pytest.mark.parametrize(
        "obj", ["1,2,3,4", (1, 2, 3, 4), Region(1, 2, 3, 4)]
    )
    def test_to_region(self, obj):
        """
        Test that supported inputs are converted to a Region.
        """
        assert to_region(obj) == Region(1, 2, 3, 4)

    def test_none(self):
        """
        Test that None is passed through.
        """
        assert to_point(None) is None
        assert to_region(None) is None


class TestPoint:
    def test_point(self):
        """
        Test the point helpers.
        """
        point = Point("1", 2.5)
        assert point.as_tuple() == (1, 2)
        assert tuple(point) == (1, 2)
        assert str(point) == "point:1,2"
        assert point.move(2, "3") == Point(3, 5)


class TestRegion:
    @pytest.mark.parametrize(
        "coordinates, message",
        [((2, 0, 1, 1), "Invalid width"), ((0, 2, 1, 1), "Invalid height")],
    )
    def test_invalid(self, coordinates, message):
        """
        Test that empty regions are rejected.
        """
        with pytest.raises(ValueError, match=message):
            Region(*coordinates)

    def test_basics(self):
        """
        Test the region properties and conversions.
        """
        region = Region.from_size(1, 2, 10, 20)
        assert region == Region(1, 2, 11, 22)
        assert region.as_tuple() == (1, 2, 11, 22)
        assert tuple(region) == (1, 2, 11, 22)
        assert str(region) == "region:1,2,11,22"
        assert region.width == 10
        assert region.height == 20
        assert region.area == 200
        assert region.center == Point(6, 12)

    def test_merge(self):
        """
        Test that merging returns the bounding region.
        """
        merged = Region.merge([Region(0, 5, 2, 6), Region(1, 1, 4, 3)])
        assert merged == Region(0, 1, 4, 6)

    def test_set_size(self):
        """
        Test that setting the size resizes the region around its center.
        """
        region = Region(10, 10, 20, 20)
        region.width = 20
        region.height = 4
        assert region == Region(5, 13, 25, 17)

    @pytest.mark.parametrize("attribute", ["width", "height"])
    def test_set_size_invalid(self, attribute):
        """
        Test that setting a non-positive size is rejected.
        """
        region = Region(0, 0, 10, 10)
        with pytest.raises(ValueError, match=f"Invalid {attribute}"):
            setattr(region, attribute, 0)

    def test_scale(self):
        """
        Test that scaling multiplies all coordinates.
        """
        assert Region(1, 2, 3, 4).scale(1.5) == Region(1, 3, 4, 6)

    @pytest.mark.parametrize(
        "sizes, expected",
        [
            ((1,), Region(9, 9, 21, 21)),
            ((1, 2), Region(9, 8, 21, 22)),
            ((1, 2, 3), Region(9, 8, 23, 22)),
            ((1, 2, 3, 4), Region(9, 8, 23, 24)),
        ],
    )
    def test_resize(self, sizes, expected):
        """
        Test the different ways to resize a region.
        """
        assert Region(10, 10, 20, 20).resize(*sizes) == expected

    @pytest.mark.parametrize("sizes", [(), (1, 2, 3, 4, 5)])
    def test_resize_invalid(self, sizes):
        """
        Test that an invalid number of sizes is rejected.
        """
        with pytest.raises(ValueError, match="Invalid number"):
            Region(10, 10, 20, 20).resize(*sizes)

    def test_move(self):
        """
        Test that moving keeps the region size.
        """
        assert Region(1, 2, 3, 4).move(10, "20") == Region(11, 22, 13, 24)

    @pytest.mark.parametrize(
        "element, expected",
        [
            (Point(0, 10), True),
            (Point(11, 5), False),
            (Region(1, 1, 10, 10), True),
            (Region(1, 1, 11, 10), False),
        ],
    )
    def test_contains(self, element, expected):
        """
        Test that points and regions are checked edges included.
        """
        assert Region(0, 0, 10, 10).contains(element) is expected

    def test_contains_invalid(self):
        """
        Test that unsupported elements are rejected.
        """
        with pytest.raises(TypeError):
            Region(0, 0, 10, 10).contains((1, 1))  # type: ignore[arg-type]

    def test_clamp(self):
        """
        Test that clamping limits the region to the container.
        """
        container = Region(0, 0, 10, 10)
        assert Region(-5, 2, 15, 8).clamp(container) == Region(0, 2, 10, 8)
