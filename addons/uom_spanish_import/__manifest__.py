# -*- coding: utf-8 -*-
{
    'name': 'UoM Spanish Import Fix',
    'version': '18.0.1.0.0',
    'category': 'Product',
    'summary': 'Fix UoM matching for Spanish language imports',
    'description': """
UoM Spanish Import Fix
======================

This module solves the issue where Odoo's standard import (base_import) cannot 
match Spanish unit of measure names during product imports.

**Problem:**
The uom.uom name field is stored as a translated JSON field:
  {'en_US': 'Units', 'es_419': 'Unidades'}

When importing products with Spanish unit names (e.g., "Unidades", "g", "kg"),
the standard =ilike search doesn't work on JSON fields, causing:
  - "No se encontraron registros que coincidan con el siguiente nombre en el campo Unidad"
  - "null value in column uom_id violates not-null constraint"

**Solution:**
This module overrides the _match_records method in base_import to use SQL-based
JSON text search that properly matches Spanish unit names against translated fields.

**Supported Spanish Units:**
- Unidades, Unidad, u, units → Unidades
- Gramo, Gramos, g, gr → g
- Kilogramo, Kilogramos, Kilo, Kilos, kg → kg
- Mililitro, Mililitros, ml → ml
- Litro, Litros, l, L → L
- Metro, Metros, m → m
- Centímetro, Centímetros, cm → cm
- Milímetro, Milímetros, mm → mm
- Hora, Horas, h → Hours
- Día, Días, day, days → Days
- Minuto, Minutos, min → Minutes
- Onza, Onzas, oz → oz
- Libra, Libras, lb → lb
- Tonelada, Toneladas, ton → Ton
- Pie, Pies, ft → ft
- Pulgada, Pulgadas, in → in
- Yarda, Yardas, yd → yd
- Milla, Millas, mi → mi

**Usage:**
1. Install this module
2. Import products as usual using Odoo's standard import
3. Spanish unit names will be automatically matched

**Compatible with:**
- Odoo 18.0 Community Edition
- Any import that uses uom_id field (product.template, product.product)
    """,
    'author': 'Marcelo Pesallaccia',
    'website': 'https://github.com/marcelompz',
    'license': 'LGPL-3',
    'depends': [
        'product',
    ],
    'data': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'external_dependencies': {
        'python': [],
    },
}
