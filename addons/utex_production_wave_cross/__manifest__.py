# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Ola de producción',
    'summary': 'Módulo para generar olas de producción',
    'description': '''
        - Con este modulo se puede seleccionar las cotizaciones confirmadas para crear olas de producción y luego traslados internos de materiales 
          a las ubicaciones seleccionadas.
    ''',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Uncategorized',
    'version': '25.12.8',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_actions_server.xml',
        'data/ir_sequence.xml',
        'views/production_wave.xml',
        'views/product_template.xml',
    ],
}
