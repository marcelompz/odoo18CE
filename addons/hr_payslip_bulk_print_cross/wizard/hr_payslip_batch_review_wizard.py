# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrPayslipBatchReviewWizard(models.TransientModel):
    _name = 'hr.payslip.batch.review.wizard'
    _description = 'Wizard Revisar Lote de Nómina'

    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True)
    company_id = fields.Many2one('res.company', string='Empresa', required=True,
                                 default=lambda self: self.env.company)
    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='Empleados con marcaciones',
        help='Empleados activos que tienen marcaciones en el período seleccionado.',
    )
    selected_payslip_ids = fields.Many2many(
        comodel_name='hr.payslip',
        string='Recibos del lote',
        help='Recibos generados para el lote de nómina. Seleccione los que desea confirmar o imprimir.',
    )
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lote de Nómina')
    generated_payslip_count = fields.Integer(
        string='Recibos calculados',
        compute='_compute_generated_payslip_count',
    )
    state = fields.Selection(
        selection=[('config', 'Configurar'), ('generated', 'Lote calculado')],
        string='Estado',
        default='config',
        readonly=True,
    )

    @api.depends('payslip_run_id')
    def _compute_generated_payslip_count(self):
        for rec in self:
            rec.generated_payslip_count = len(rec.selected_payslip_ids)

    def _ensure_dates(self):
        for rec in self:
            if not rec.date_from or not rec.date_to:
                raise UserError(_('Debe elegir un rango de fechas.'))
            if rec.date_from > rec.date_to:
                raise UserError(_('La fecha Desde no puede ser mayor que la fecha Hasta.'))

    def _attendance_employees(self):
        self.ensure_one()
        Att = self.env['hr.attendance']
        domain = [
            ('employee_id.active', '=', True),
        ]
        if 'shift_date' in Att._fields:
            domain += [
                ('shift_date', '>=', self.date_from),
                ('shift_date', '<=', self.date_to),
            ]
        else:
            date_from_dt = fields.Datetime.to_datetime(self.date_from)
            date_to_dt = fields.Datetime.to_datetime(self.date_to).replace(
                hour=23, minute=59, second=59,
            )
            domain += [
                ('check_in', '>=', date_from_dt),
                ('check_in', '<=', date_to_dt),
            ]
        attendances = Att.search(domain)
        return self.env['hr.employee'].browse(attendances.mapped('employee_id').ids)

    def action_find_employees(self):
        self.ensure_one()
        self._ensure_dates()
        employees = self._attendance_employees()
        if not employees:
            raise UserError(_('No se encontraron empleados con marcaciones en el período seleccionado.'))
        self.employee_ids = employees
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Empleados encontrados'),
                'message': _('%d empleados con marcaciones cargados.') % len(employees),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_calculate_batch(self):
        self.ensure_one()
        self._ensure_dates()
        employees = self.employee_ids or self._attendance_employees()
        if not employees:
            raise UserError(_('No hay empleados disponibles para generar el lote.'))

        run = self.env['hr.payslip.run'].create({
            'name': _('Lote de Nómina %s - %s') % (self.date_from, self.date_to),
            'date_start': self.date_from,
            'date_end': self.date_to,
            'company_id': self.company_id.id,
            'state': 'draft',
        })

        slips = self.env['hr.payslip']

        for employee in employees:
            contract = employee.contract_ids.filtered(lambda c: c.state == 'open')
            if not contract:
                continue
            contract = contract[0]
            payslip = self.env['hr.payslip'].create({
                'employee_id': employee.id,
                'contract_id': contract.id,
                'struct_id': contract.struct_id.id,
                'payslip_run_id': run.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
            })
            slips |= payslip

        if not slips:
            run.unlink()
            raise UserError(_('No se pudo generar ningún recibo. Verifique que los empleados tengan contrato activo.'))

        slips.compute_sheet()
        self.selected_payslip_ids = slips
        self.payslip_run_id = run
        self.state = 'generated'

        return self._action_open_run()

    def action_confirm_selected(self):
        self.ensure_one()
        if not self.selected_payslip_ids:
            raise UserError(_('Seleccione al menos un recibo para confirmar.'))
        slips = self.selected_payslip_ids.filtered(lambda s: s.state in ('draft', 'verify'))
        if not slips:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nada por confirmar'),
                    'message': _('Los recibos seleccionados ya están confirmados o en estado final.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        slips.compute_sheet()
        slips.action_payslip_done()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Lote confirmado'),
                'message': _('Los recibos seleccionados han sido confirmados.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_print_selected(self):
        self.ensure_one()
        if not self.selected_payslip_ids:
            raise UserError(_('Seleccione al menos un recibo para imprimir.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imprimir Recibos Seleccionados'),
            'res_model': 'hr.payslip.bulk.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_ids': [(6, 0, self.selected_payslip_ids.ids)],
                'default_state_filter': 'all',
            },
        }

    def _ensure_run_and_selection(self):
        if not self.payslip_run_id:
            raise UserError(_('Aún no se ha generado el lote de nómina.'))
        if not self.selected_payslip_ids:
            raise UserError(_('Seleccione al menos un recibo para finalizar el lote.'))

    def action_open_selected_payslips(self):
        self.ensure_one()
        if not self.selected_payslip_ids:
            raise UserError(_('No hay recibos seleccionados para abrir.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recibos seleccionados'),
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.selected_payslip_ids.ids)],
            'context': {'default_payslip_run_id': self.payslip_run_id.id if self.payslip_run_id else False},
        }

    def action_finalize_run(self):
        """Quita del lote los recibos no seleccionados y valida el lote."""
        self.ensure_one()
        self._ensure_run_and_selection()
        run = self.payslip_run_id
        # Desvincular los recibos que NO fueron seleccionados
        to_keep = self.selected_payslip_ids
        to_remove = run.slip_ids - to_keep
        if to_remove:
            to_remove.write({'payslip_run_id': False})

        # Asegurar que los recibos restantes esten calculados y confirmar el run
        remaining = run.slip_ids
        if remaining:
            remaining.compute_sheet()
        # Validar/confirmar el lote usando el método estándar del run
        if hasattr(run, 'action_validate'):
            run.action_validate()
        else:
            # Fallback: confirmar payslips individualmente
            remaining.action_payslip_done()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Lote finalizado'),
                'message': _('El lote fue finalizado con los recibos seleccionados.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_finalize_and_print(self):
        """Finaliza el lote (quedando solo los seleccionados) y abre el wizard de impresion."""
        self.ensure_one()
        self.action_finalize_run()
        # Abrir wizard de impresion con los recibos finales del lote
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imprimir Recibos del Lote'),
            'res_model': 'hr.payslip.bulk.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_ids': [(6, 0, self.payslip_run_id.slip_ids.ids)],
                'default_state_filter': 'all',
            },
        }

    def action_open_run(self):
        self.ensure_one()
        if not self.payslip_run_id:
            raise UserError(_('Aún no se ha generado el lote de nómina.'))
        return self._action_open_run()

    def _action_open_run(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lote de Nómina'),
            'res_model': 'hr.payslip.run',
            'view_mode': 'form',
            'res_id': self.payslip_run_id.id,
            'target': 'current',
        }
