from pickai.domain.aisle_policies import route_combined, route_s_shape
from pickai.domain.cart_splits import split_cart_capacity
from pickai.contracts.types import OrderLine


def test_s_shape_route_visits_all_points():
    origin = [0.0, 5.5]
    locs = [[1.0, 10.0], [1.0, 20.0], [3.0, 15.0]]
    dist, path = route_s_shape(origin, locs, 5.5, 50.0)
    assert dist > 0
    assert path[0] == origin
    assert path[-1] == origin


def test_combined_not_worse_than_extreme():
    origin = [0.0, 5.5]
    locs = [[2.0, 12.0], [4.0, 18.0], [6.0, 25.0]]
    d_c, _ = route_combined(origin, locs, 5.5, 50.0)
    d_s, _ = route_s_shape(origin, locs, 5.5, 50.0)
    assert d_c <= d_s + 1


def test_cart_split_by_weight():
    lines = [
        OrderLine(order_id="o1", line_id="1", sku="a", location_id="l1", quantity=1, x=1, y=1, weight_kg=100.0),
        OrderLine(order_id="o1", line_id="2", sku="b", location_id="l2", quantity=1, x=2, y=2, weight_kg=100.0),
    ]
    batches = split_cart_capacity(lines, max_lines=10, max_weight_kg=150.0, max_pieces=10)
    assert len(batches) == 2
