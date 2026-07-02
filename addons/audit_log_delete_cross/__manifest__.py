# -*- coding: utf-8 -*-
{
    'name': 'Crossnexion - Registro de Auditoría de Eliminaciones',
    'summary': 'Registra todos los registros eliminados en el sistema para fines de auditoría.',
    'author': 'Crossnexion EAS',
    'website': 'www.crossnexion.com',
    'license': 'OPL-1',
    'category': 'Extra Tools',
    'version': '25.08.14',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/audit_log_delete.xml',
    ],
}
