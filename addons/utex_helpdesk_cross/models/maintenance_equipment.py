# -*- coding: utf-8 -*-
"""
Created on 2025-12-05 08:48:09

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class MaintenanceEquipmentInherit(models.Model):
    _inherit = 'maintenance.equipment'

    label_number = fields.Char(
        string='Nro. etiqueta')

    @api.depends('name', 'model', 'label_number')
    def _compute_display_name(self):
        for record in self:
            parts = [record.name, record.model, record.label_number]
            clean_parts = [str(p) for p in parts if p]
            record.display_name = " - ".join(clean_parts)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        results_super = super().name_search(name=name, args=args, operator=operator, limit=limit)
        found_ids = [res[0] for res in results_super]

        if name and (limit is None or len(results_super) < limit):
            remaining_limit = limit - len(results_super) if limit else None
            
            search_domain = [
                '|', 
                ('label_number', operator, name),
                ('model', operator, name)
            ]
            
            domain_with_exclusion = expression.AND([
                search_domain, 
                [('id', 'not in', found_ids)]
            ])
            
            final_domain = expression.AND([args or [], domain_with_exclusion])
            
            custom_recs = self.search(final_domain, limit=remaining_limit)
            
            if custom_recs:
                results_super.extend([(rec.id, rec.display_name) for rec in custom_recs])
            
            return results_super
            
        return results_super
