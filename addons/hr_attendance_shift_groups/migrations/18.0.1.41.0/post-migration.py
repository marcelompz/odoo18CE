# -*- coding: utf-8 -*-
# Crossnexion - separacion del limite extra/descuento en ENTRADA y SALIDA.
# Copia el valor del campo legacy (hard_limit_minutes) a los dos campos nuevos
# para PRESERVAR el comportamiento actual de los grupos existentes. Corre una
# sola vez al actualizar a 18.0.1.41.0.


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_shift_group
           SET hard_limit_entry_minutes = COALESCE(NULLIF(hard_limit_minutes, 0), 30),
               hard_limit_exit_minutes  = COALESCE(NULLIF(hard_limit_minutes, 0), 30)
    """)
