def migrate(cr, version=None):
    cr.execute(
        """
        update fleet_vehicle_odometer
        set driver_id=fleet_vehicle.driver_id
        from fleet_vehicle
        where fleet_vehicle.id=fleet_vehicle_odometer.vehicle_id
        """
    )
