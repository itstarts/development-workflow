"""Minimal fictional order model for planning evaluations."""


def create_order(order_id, owner):
    return {"id": order_id, "owner": owner, "status": "created"}
