def post_init_hook(cr, registry):
    _init_fleet_vehicle_driver(cr)


def _init_fleet_vehicle_driver(cr):
    cr.execute(
        """
        insert into fleet_vehicle_driver (vehicle_id, driver_id, date_start)
        select id, driver_id, create_date from fleet_vehicle where driver_id is not null
        """
    )
