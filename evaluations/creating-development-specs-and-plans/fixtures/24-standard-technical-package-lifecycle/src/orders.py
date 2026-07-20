"""Minimal internal order export model for planning evaluations."""


def create_order(order_id, owner, status="pending"):
    return {"id": order_id, "owner": owner, "status": status}


def export_orders(orders):
    return [dict(order) for order in orders]
