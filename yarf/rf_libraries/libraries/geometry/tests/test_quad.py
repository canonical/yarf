from yarf.rf_libraries.libraries.geometry.quad import Quad
from yarf.vendor.RPA import Region


class TestGeometry:
    def test_quad_to_region(self):
        quad = Quad([[0, 0], [1, 0], [1, 1], [0, 1]])
        result = quad.to_region()
        assert result == Region(0, 0, 1, 1)
