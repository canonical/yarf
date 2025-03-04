from RPA.core.geometry import Region

from yarf.rf_libraries.libraries.camera.utils import Quad, quad_to_region


class TestUtils:
    def test_quad_iterator(self):
        quad = Quad(
            top_left=[0, 0],
            top_right=[1, 0],
            bottom_right=[1, 1],
            bottom_left=[0, 1],
        )
        result = list(quad)
        assert result == [[0, 0], [1, 0], [1, 1], [0, 1]]

    def test_quad_to_region(self):
        quad = Quad([0, 0], [1, 0], [1, 1], [0, 1])
        result = quad_to_region(quad)
        assert result == Region(0, 0, 1, 1)
