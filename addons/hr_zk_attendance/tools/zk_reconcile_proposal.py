# -*- coding: utf-8 -*-
"""Genera una PROPUESTA de mapeo device_id -> empleado real.
SOLO LECTURA: no modifica nada en Odoo ni en el reloj.

Empareja cada usuario del reloj contra los empleados de Odoo por nombre
normalizado (sin acentos, mayusculas, sin puntuacion). Marca:
  EXACTO   -> nombre normalizado identico
  SIMILAR  -> uno es subconjunto de tokens del otro (abreviaciones), >=2 tokens
  SIN_MATCH-> no se encontro empleado activo

Salida CSV (separador '|') para revision humana.
"""
import re
import unicodedata
from zk import ZK
import psycopg2

DEVICE_IP = '190.128.211.22'
DEVICE_PORT = 4370
DB_HOST = 'db_odoo_5766'
DB_NAME = 'prod_20_04_2026'
DB_USER = 'odoo'
DB_PASS = 'odoo'


def norm(s):
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = s.upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def tokens(s):
    return set(t for t in norm(s).split() if len(t) > 1)


# --- usuarios del reloj (solo lectura) ------------------------------------
zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=25, password=0, ommit_ping=True)
conn = zk.connect()
dev_users = [(str(u.user_id).strip(), (u.name or '').strip())
             for u in conn.get_users()]
conn.disconnect()

# --- empleados de Odoo (excluye los ya fusionados) ------------------------
pg = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER,
                      password=DB_PASS)
cur = pg.cursor()
cur.execute("""
    SELECT id, name, device_id_num, active
      FROM hr_employee
     WHERE coalesce(name,'') NOT LIKE '[FUSIONADO%'
""")
emps = [(eid, name, did, active, norm(name), tokens(name))
        for (eid, name, did, active) in cur.fetchall()]
pg.close()


def find_match(dname):
    dn = norm(dname)
    dt = tokens(dname)
    # 1) exacto entre activos
    exact = [e for e in emps if e[4] == dn and e[3]]
    if exact:
        return exact[0], 'EXACTO'
    # 2) similar: subconjunto de tokens, comparte >=2 (incluye apellido)
    cand = []
    for e in emps:
        if not e[3]:
            continue
        et = e[5]
        common = dt & et
        if dt and et and (dt <= et or et <= dt) and len(common) >= 2:
            cand.append((len(common), e))
    if cand:
        cand.sort(reverse=True, key=lambda x: x[0])
        return cand[0][1], 'SIMILAR'
    return None, 'SIN_MATCH'


print('device_id|device_name|match_type|emp_id|emp_name|emp_device_id_actual|emp_activo')
n_exact = n_sim = n_none = 0
for did, dname in sorted(dev_users,
                         key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
    e, mt = find_match(dname)
    if mt == 'EXACTO':
        n_exact += 1
    elif mt == 'SIMILAR':
        n_sim += 1
    else:
        n_none += 1
    if e:
        print('|'.join([did, dname, mt, str(e[0]), e[1] or '',
                        str(e[2] or ''), 'A' if e[3] else 'X']))
    else:
        print('|'.join([did, dname, mt, '', '', '', '']))

print('---RESUMEN---')
print('Total usuarios reloj: %d | EXACTO: %d | SIMILAR: %d | SIN_MATCH: %d'
      % (len(dev_users), n_exact, n_sim, n_none))
