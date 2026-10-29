TRANSITIONS = {
    "requested": {"pickup_scheduled", "cancelled", "exception"},
    "pickup_scheduled": {"picked_up", "cancelled", "exception"},
    "picked_up": {"in_transit", "exception"},
    "in_transit": {"out_for_delivery", "exception"},
    "out_for_delivery": {"delivered", "exception"},
    "exception": {"in_transit", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}
