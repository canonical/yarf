from RPA.core.geometry import Region

from yarf.rf_libraries.libraries.geometry.quad import Quad


class TestGeometry:
    def test_quad_to_region(self):
        quad = Quad([[0, 0], [1, 0], [1, 1], [0, 1]])
        result = quad.to_region()
        assert result == Region(0, 0, 1, 1)
