# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrAdvance(models.Model):
    _name = 'hr.advance'
    _description = 'Anticipo de Sueldo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Numero', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nuevo'))
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True, readonly=True)
    date = fields.Date(string='Fecha del anticipo', default=fields.Date.context_today, required=True)
    amount = fields.Monetary(string='Monto', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    description = fields.Char(string='Descripcion')
    journal_id = fields.Many2one('account.journal', string='Diario de pago',
                                  domain=[('type', 'in', ('cash', 'bank'))])
    advance_account_id = fields.Many2one('account.account', string='Cuenta Anticipo a Empleados')
    payment_id = fields.Many2one('account.payment', string='Pago', readonly=True, copy=False)
    salary_attachment_id = fields.Many2one('hr.salary.attachment', string='Attachment salarial',
                                            readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('rrhh_approved', 'Aprobado RRHH'),
        ('paid', 'Desembolsado'),
        ('deducted', 'Descontado'),
        ('cancelled', 'Cancelado'),
    ], default='draft', tracking=True, string='Estado')
    rrhh_approver_id = fields.Many2one('res.users', readonly=True)
    finance_approver_id = fields.Many2one('res.users', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.advance') or _('Nuevo')
        return super().create(vals_list)

    def action_rrhh_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Solo se puede aprobar (RRHH) un anticipo en estado Borrador.'))
            if not self.env.user.has_group('hr_payroll.group_hr_payroll_user'):
                raise UserError(_('Solo el grupo de RRHH puede dar la primera aprobacion.'))
            rec.write({'state': 'rrhh_approved', 'rrhh_approver_id': self.env.user.id})

    def action_finance_pay(self):
        for rec in self:
            if rec.state != 'rrhh_approved':
                raise UserError(_('El anticipo debe estar aprobado por RRHH antes de desembolsar.'))
            if not self.env.user.has_group('account.group_account_manager'):
                raise UserError(_('Solo el grupo de Finanzas puede desembolsar.'))
            if not rec.journal_id or not rec.advance_account_id:
                raise UserError(_('Configure el Diario de pago y la Cuenta de Anticipo antes de desembolsar.'))
            rec._create_payment_and_attachment()

    def action_cancel(self):
        for rec in self:
            if rec.state in ('paid', 'deducted'):
                raise UserError(_('No se puede cancelar un anticipo ya desembolsado.'))
            rec.state = 'cancelled'

    def action_back_to_draft(self):
        for rec in self:
            if rec.state == 'cancelled':
                rec.state = 'draft'

    def _create_payment_and_attachment(self):
        self.ensure_one()
        Payment = self.env['account.payment'].sudo()
        partner = self.employee_id.work_contact_id or self.employee_id.user_id.partner_id
        if not partner:
            raise UserError(_('El empleado %s no tiene contacto/partner asociado.') % self.employee_id.name)

        payment = Payment.create({
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'payment_type': 'outbound',
            'memo': _('Anticipo de sueldo %s - %s') % (self.name, self.employee_id.name),
            'destination_account_id': self.advance_account_id.id,
        })
        payment.action_post()

        Attachment = self.env['hr.salary.attachment'].sudo()
        desc = self.description or (_('Anticipo - %s') % self.name)

        # Tipo de entrada en nomina (requerido en Odoo 18)
        input_type = self.env.ref(
            'hr_loan_advance_py_cross.hr_payslip_input_type_anticipo',
            raise_if_not_found=False,
        )
        if not input_type:
            raise UserError(_('Falta el tipo de entrada de nomina "Anticipo de Sueldo". Reinstale el modulo.'))

        attachment_vals = {
            'description': desc,
            'monthly_amount': self.amount,
            'total_amount': self.amount,
            'date_start': self.date,
            'state': 'open',
            'other_input_type_id': input_type.id,
        }
        if 'employee_ids' in Attachment._fields:
            attachment_vals['employee_ids'] = [(4, self.employee_id.id)]
        elif 'employee_id' in Attachment._fields:
            attachment_vals['employee_id'] = self.employee_id.id
        attachment = Attachment.create(attachment_vals)

        self.write({
            'state': 'paid',
            'payment_id': payment.id,
            'salary_attachment_id': attachment.id,
            'finance_approver_id': self.env.user.id,
        })
        self.message_post(body=_('Anticipo desembolsado. Pago: %s. Attachment: %s')
                              % (payment.name, attachment.id))

    def action_view_payment(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError(_('No hay pago registrado.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Pago'),
            'res_model': 'account.payment', 'view_mode': 'form',
            'res_id': self.payment_id.id,
        }

    def action_view_attachment(self):
        self.ensure_one()
        if not self.salary_attachment_id:
            raise UserError(_('No hay attachment registrado.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Attachment'),
            'res_model': 'hr.salary.attachment', 'view_mode': 'form',
            'res_id': self.salary_attachment_id.id,
        }
