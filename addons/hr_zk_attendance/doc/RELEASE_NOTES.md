## Module <hr_zk_attendance>

#### 04.06.2026
#### Version 18.0.1.4.0
##### FIX (Crossnexion)

- `models/hr_attendance.py` (NUEVO): override de `_check_validity` de Odoo core.
  Se mantiene el control de SOLAPAMIENTO pero se PERMITEN multiples marcaciones
  abiertas (sin check_out) por empleado. Necesario porque un dia de un solo
  fichaje queda abierto a proposito (para corregir la salida) y el core de Odoo
  prohibia 2+ abiertas, lo que hacia fallar la descarga masiva del reloj.
  IMPORTANTE: cambios de codigo .py requieren REINICIAR el contenedor (no basta -u).

#### 04.06.2026
#### Version 18.0.1.3.0
##### FIX (Crossnexion)

- Re-deploy del modulo completo. En el servidor de test estaba incompleto (faltaba
  el __init__.py raiz, todo wizard/, 3 de 4 vistas y modelos), lo que rompia el
  upgrade con FileNotFoundError. Reconstruido desde la copia local completa.

#### 26.03.2025
#### Version 18.0.1.0.0
##### ADD

- Initial commit for Biometric Device Integration
