# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError

from .. import hooks


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    def action_apply_cn_py_rules(self):
        if not self:
            raise UserError(_('Seleccione al menos una estructura salarial.'))

        env = self.env
        Rule = env['hr.salary.rule'].sudo()

        cat_basic = hooks._get_or_skip(env, 'BASIC')
        cat_alw = hooks._get_or_skip(env, 'ALW')
        cat_ded = hooks._get_or_skip(env, 'DED')
        cat_net = hooks._get_or_skip(env, 'NET')
        cat_employer = env.ref(
            'hr_payroll_rules_py_cross.hr_salary_rule_category_cn_py_employer',
            raise_if_not_found=False,
        )
        cat_info = env.ref(
            'hr_payroll_rules_py_cross.hr_salary_rule_category_cn_py_info',
            raise_if_not_found=False,
        )
        if not cat_alw:
            cat_alw = env['hr.salary.rule.category'].sudo().create({
                'name': 'Asignaciones',
                'code': 'ALW',
            })
        if not (cat_basic and cat_ded and cat_net):
            raise UserError(_('No se encontraron las categorias estandar BASIC/DED/NET.'))

        rules_def = hooks._build_rules_def(
            cat_basic, cat_alw, cat_ded, cat_net, cat_employer, cat_info,
        )

        created = updated = 0
        for struct in self:
            for rdef in rules_def:
                existing = Rule.search([
                    ('struct_id', '=', struct.id),
                    ('code', '=', rdef['code']),
                ], limit=1)
                if existing:
                    existing.write({
                        'amount_python_compute': rdef['amount_python_compute'],
                        'condition_python': rdef['condition_python'],
                        'category_id': rdef['category_id'],
                        'sequence': rdef['sequence'],
                    })
                    updated += 1
                    continue
                vals = dict(rdef)
                vals.update({
                    'struct_id': struct.id,
                    'condition_select': 'python',
                    'amount_select': 'code',
                    'active': True,
                })
                Rule.create(vals)
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reglas aplicadas'),
                'message': _('%d creadas, %d actualizadas en %d estructura(s).') % (
                    created, updated, len(self),
                ),
                'type': 'success',
                'sticky': False,
            },
        }
