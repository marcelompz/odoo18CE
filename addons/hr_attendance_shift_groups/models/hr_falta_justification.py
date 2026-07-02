# -*- coding: utf-8 -*-
"""Solicitud de justificacion de FALTAS detectadas en el Tablero Diario.

Flujo:
1) Empleado/RRHH selecciona dias con FALTA en el Tablero Diario y crea
   una hr.falta.justification con motivo (olvido, enfermedad, vacaciones,
   otros) y descripcion.
2) La solicitud va al supervisor del empleado (parent_id) en estado 'pending'.
3) Supervisor revisa y Aprueba o Rechaza.
4) Al Aprobar:
   - Las filas del Tablero Diario referenciadas se marcan como
     absence_status='leave' (ausencia justificada) con el motivo.
   - Si motivo='enfermedad' o 'vacaciones', se sugiere crear el hr.leave
     correspondiente (manualmente, para que el departamento de RRHH lo
     procese formalmente).
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrFaltaJustification(models.Model):
    _name = 'hr.falta.justification'
    _description = 'Justificacion de Falta (Crossnexion)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', readonly=True, copy=False,
                       default=lambda s: _('Nueva'))
    employee_id = fields.Many2one('hr.employee', string='Empleado',
                                  required=True, tracking=True,
                                  ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id',
                                    store=True, string='Departamento')
    manager_id = fields.Many2one('hr.employee', string='Supervisor',
                                 compute='_compute_manager_id', store=True,
                                 help='Supervisor directo (parent_id) del '
                                      'empleado al momento de la solicitud.')
    daily_report_ids = fields.Many2many(
        'hr.attendance.daily.report',
        'hr_falta_just_daily_rel', 'just_id', 'report_id',
        string='Dias a justificar', required=True,
    )
    days_count = fields.Integer(string='Cantidad de dias',
                                compute='_compute_days_count', store=True)
    date_from = fields.Date(string='Fecha desde',
                            compute='_compute_date_range', store=True)
    date_to = fields.Date(string='Fecha hasta',
                          compute='_compute_date_range', store=True)
    reason = fields.Selection([
        ('olvido', 'Olvido de marcacion'),
        ('enfermedad', 'Ausencia por enfermedad'),
        ('vacaciones', 'Vacaciones / Permiso'),
        ('otros', 'Otros motivos'),
    ], string='Motivo', required=True, tracking=True)
    description = fields.Text(string='Descripcion', tracking=True,
                              help='Detalle del motivo. Adjuntar documentacion '
                                   'medica u otros respaldos en el chatter.')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente aprobacion'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ], string='Estado', default='draft', tracking=True, required=True)
    approver_id = fields.Many2one('res.users', string='Aprobador',
                                  readonly=True, tracking=True)
    approval_date = fields.Datetime(string='Fecha de aprobacion',
                                    readonly=True)
    rejection_reason = fields.Text(string='Motivo de rechazo')

    @api.depends('employee_id', 'employee_id.parent_id')
    def _compute_manager_id(self):
        for rec in self:
            rec.manager_id = rec.employee_id.parent_id

    @api.depends('daily_report_ids')
    def _compute_days_count(self):
        for rec in self:
            rec.days_count = len(rec.daily_report_ids)

    @api.depends('daily_report_ids')
    def _compute_date_range(self):
        for rec in self:
            dates = rec.daily_report_ids.mapped('date')
            rec.date_from = min(dates) if dates else False
            rec.date_to = max(dates) if dates else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                seq = self.env['ir.sequence'].next_by_code('hr.falta.justification')
                vals['name'] = seq or _('FALTA-NUEVA')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.daily_report_ids:
                raise UserError(_('Debe seleccionar al menos un dia.'))
            if not rec.reason:
                raise UserError(_('Debe seleccionar un motivo.'))
            rec.write({'state': 'pending'})
            rec.daily_report_ids.write({
                'request_state': 'pending',
                'justification_id': rec.id,
            })
            # Notificar al supervisor por chatter
            if rec.manager_id and rec.manager_id.user_id:
                rec.message_post(
                    body=_('Solicitud de justificacion enviada para aprobacion.'),
                    partner_ids=[rec.manager_id.user_id.partner_id.id],
                )

    def action_approve(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Solo se puede aprobar solicitudes pendientes.'))
            rec.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })
            # Reclasificar las filas del Tablero
            label = dict(self._fields['reason'].selection).get(rec.reason)
            for row in rec.daily_report_ids:
                row.write({
                    'absence_status': 'leave',
                    'leave_type_name': '%s (Aprobado)' % label,
                    'is_missing': False,
                    'has_attendance': False,
                    'request_state': 'approved',
                })
            rec.message_post(body=_('Solicitud aprobada. %d dias re-clasificados '
                                    'como ausencia justificada.') % rec.days_count)

    def action_reject(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Solo se puede rechazar solicitudes pendientes.'))
            if not rec.rejection_reason:
                raise UserError(_('Indique un motivo de rechazo antes de continuar.'))
            rec.write({
                'state': 'rejected',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })
            rec.daily_report_ids.write({
                'request_state': 'rejected',
            })
            rec.message_post(body=_('Solicitud rechazada: %s') % rec.rejection_reason)

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})
            rec.daily_report_ids.write({'request_state': False})

    def action_view_daily_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dias de la solicitud'),
            'res_model': 'hr.attendance.daily.report',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.daily_report_ids.ids)],
        }
