# -*- coding: utf-8 -*-
"""Acciones extra y campos calculados de cumpleaños para el portal."""
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Campos calculados para la vista de cumpleaños
    birthday_day_label = fields.Char(
        string='Cumpleanos',
        compute='_compute_birthday_info',
        help='Texto: "15 de Marzo" o "HOY!".',
    )
    birthday_days_until = fields.Integer(
        string='Dias hasta el cumple',
        compute='_compute_birthday_info',
    )
    birthday_is_today = fields.Boolean(
        string='Cumple hoy',
        compute='_compute_birthday_info',
    )
    birthday_age = fields.Integer(
        string='Edad que cumple',
        compute='_compute_birthday_info',
    )

    MONTHS_ES = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ]

    @api.depends('birthday')
    def _compute_birthday_info(self):
        today = date.today()
        for rec in self:
            rec.birthday_day_label = ''
            rec.birthday_days_until = 0
            rec.birthday_is_today = False
            rec.birthday_age = 0
            if not rec.birthday:
                continue
            bday = rec.birthday
            month = bday.month
            day = bday.day
            month_name = self.MONTHS_ES[month] if 0 < month < 13 else ''
            # Cumpleaños este año
            try:
                next_bday = date(today.year, month, day)
            except ValueError:
                # 29 de febrero en año no bisiesto
                next_bday = date(today.year, 3, 1)
            if next_bday < today:
                try:
                    next_bday = date(today.year + 1, month, day)
                except ValueError:
                    next_bday = date(today.year + 1, 3, 1)
            delta = (next_bday - today).days
            rec.birthday_days_until = delta
            rec.birthday_is_today = (delta == 0)
            if delta == 0:
                rec.birthday_day_label = _('HOY!')
            else:
                rec.birthday_day_label = '%d de %s' % (day, month_name)
            # Edad que cumple
            rec.birthday_age = next_bday.year - bday.year

    @api.model
    def action_open_my_profile(self):
        emp = self.sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        if not emp:
            raise UserError(_(
                'Tu usuario no esta vinculado a ningun empleado. '
                'Contacta a Recursos Humanos.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mi Perfil'),
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': emp.id,
            'target': 'current',
        }

    @api.model
    def action_birthdays_this_month(self):
        """Cumpleaños del mes con vista kanban personalizada."""
        self.env.cr.execute("""
            SELECT id FROM hr_employee
            WHERE active = TRUE AND birthday IS NOT NULL
              AND EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE)
            ORDER BY EXTRACT(DAY FROM birthday)
        """)
        ids = [r[0] for r in self.env.cr.fetchall()]
        view_id = self.env.ref(
            'hr_portal_cross.view_hr_employee_birthday_kanban',
            raise_if_not_found=False,
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cumpleanos del mes'),
            'res_model': 'hr.employee',
            'view_mode': 'kanban,list,form',
            'views': [(view_id.id if view_id else False, 'kanban'), (False, 'list'), (False, 'form')],
            'domain': [('id', 'in', ids)],
            'context': {'search_default_group_by_department': 0},
        }

    @api.model
    def action_global_leave_calendar(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Calendario Global de Licencias'),
            'res_model': 'hr.leave',
            'view_mode': 'calendar,list,form',
            'domain': [('state', 'in', ('confirm', 'validate1', 'validate'))],
        }

    @api.model
    def action_my_pending_items(self):
        Leave = self.env['hr.leave'].sudo()
        domain = [
            ('state', 'in', ('confirm', 'validate1')),
            '|', ('manager_id.user_id', '=', self.env.user.id),
            ('user_id', '=', self.env.user.id),
        ]
        leaves = Leave.search(domain)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mis Pendientes'),
            'res_model': 'hr.leave',
            'view_mode': 'list,form,calendar',
            'domain': [('id', 'in', leaves.ids)],
        }

    @api.model
    def action_quick_search_employees(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Buscar Empleado'),
            'res_model': 'hr.employee',
            'view_mode': 'kanban,list,form',
            'domain': [('active', '=', True)],
            'context': {'search_default_group_by_department': 1},
        }

    @api.model
    def action_payroll_reports(self):
        candidates = [
            'hr_payroll.action_payslips_byemployees',
            'l10n_py_hr_payroll_report.action_hr_payroll_report_xlsx',
            'hr_payroll.action_view_hr_payslip_form',
        ]
        for xmlid in candidates:
            try:
                action = self.env.ref(xmlid)
                if action:
                    return action.read()[0] if hasattr(action, 'read') else action
            except Exception:
                continue
        raise UserError(_('No se encontraron reportes de nomina.'))

    # ------------------------------------------------------------------
    # Cron de alertas diarias de cumpleanos
    # ------------------------------------------------------------------
    @api.model
    def cron_birthday_alerts(self):
        """Tarea programada: cada manana revisa cumpleaneros del dia y
        publica un mensaje en su record + en hr.employee general."""
        today = fields.Date.today()
        self.env.cr.execute("""
            SELECT id FROM hr_employee
            WHERE active = TRUE AND birthday IS NOT NULL
              AND EXTRACT(MONTH FROM birthday) = %s
              AND EXTRACT(DAY FROM birthday) = %s
        """, (today.month, today.day))
        ids = [r[0] for r in self.env.cr.fetchall()]
        if not ids:
            return False
        Employee = self.sudo().browse(ids)
        for emp in Employee:
            age = today.year - emp.birthday.year
            msg = _(
                '<p><b>Hoy es el cumpleanos de %s!</b></p>'
                '<p>Cumple %d anios. No olvides saludarlo.</p>'
            ) % (emp.name, age)
            try:
                emp.message_post(
                    body=msg,
                    subject=_('Cumpleanos de %s') % emp.name,
                    message_type='notification',
                )
            except Exception:
                pass

            # Notificar al manager y RRHH
            partners_to_notify = []
            if emp.parent_id and emp.parent_id.user_id and emp.parent_id.user_id.partner_id:
                partners_to_notify.append(emp.parent_id.user_id.partner_id.id)
            hr_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
            if hr_group:
                for u in hr_group.users:
                    if u.partner_id:
                        partners_to_notify.append(u.partner_id.id)
            if partners_to_notify:
                try:
                    emp.message_post(
                        body=msg,
                        partner_ids=list(set(partners_to_notify)),
                        subtype_xmlid='mail.mt_comment',
                    )
                except Exception:
                    pass
        return True
