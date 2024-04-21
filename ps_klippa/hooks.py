# Copyright 2024 Hunki Enterprises BV


def pre_init_hook(cr):
    # synthesize an xmlid for the klippa user to avoid recreating it
    cr.execute(
        """
        with user_id as (
            select id from res_users where login='Klippa_energy'
        )
        insert into ir_model_data (module, name, model, res_id, noupdate)
        select 'ps_klippa', 'user_klippa', 'res.users', user_id.id, True
        from user_id
        where not exists (
            select module, name from ir_model_data
            where module='ps_klippa' and name='user_klippa'
        )
        """
    )
