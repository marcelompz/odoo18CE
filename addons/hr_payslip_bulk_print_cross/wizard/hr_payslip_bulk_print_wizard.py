# -*- coding: utf-8 -*-
"""
Wizard de Impresión Masiva de Recibos de Nómina
================================================

Permite generar múltiples PDFs de recibos de nómina (hr.payslip) en
una sola acción. El usuario puede escoger:

* El reporte/plantilla a utilizar.
* Si quiere PDFs separados (un archivo por recibo, empaquetados en un
  ZIP) o un único PDF consolidado.
* Filtros opcionales (estado del recibo).

Compatible con Odoo 18 Community y Enterprise.
"""

import base64
import io
import logging
import re
import zipfile
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _slugify(value):
    """Convierte un texto en un nombre de archivo seguro."""
    if not value:
        return ''
    value = str(value)
    value = re.sub(r'[^\w\s\-\.]', '', value, flags=re.UNICODE)
    value = re.sub(r'[\s]+', '_', value).strip('_.')
    return value[:120] or 'recibo'


class HrPayslipBulkPrintWizard(models.TransientModel):
    _name = 'hr.payslip.bulk.print.wizard'
    _description = 'Asistente de Impresión Masiva de Recibos de Nómina'

    # ------------------------------------------------------------------
    # Campos
    # ------------------------------------------------------------------
    payslip_ids = fields.Many2many(
        comodel_name='hr.payslip',
        string='Recibos de Nómina',
        required=True,
        help='Recibos seleccionados para impresión masiva.',
    )
    payslip_count = fields.Integer(
        string='Cantidad de Recibos',
        compute='_compute_payslip_count',
    )
    report_action_id = fields.Many2one(
        comodel_name='ir.actions.report',
        string='Plantilla de Reporte',
        required=True,
        domain="[('model', '=', 'hr.payslip'), ('report_type', 'in', ('qweb-pdf', 'qweb-text'))]",
        default=lambda self: self._default_report_action_id(),
        help='Reporte (ir.actions.report) que se usará para imprimir cada recibo.',
    )
    output_mode = fields.Selection(
        selection=[
            ('zip', 'PDFs separados en ZIP (uno por recibo)'),
            ('single', 'Un único PDF consolidado'),
        ],
        string='Formato de Salida',
        required=True,
        default='zip',
    )
    state_filter = fields.Selection(
        selection=[
            ('all', 'Todos los estados'),
            ('done', 'Solo Hecho / Pagado'),
            ('verify', 'Solo Por Verificar'),
            ('draft_verify_done', 'Borrador, Por Verificar y Hecho'),
        ],
        string='Filtro por Estado',
        default='all',
        help='Filtra los recibos seleccionados según su estado antes de imprimir.',
    )
    include_payslip_number = fields.Boolean(
        string='Incluir número de recibo en el nombre',
        default=True,
    )
    file_name = fields.Char(string='Nombre del Archivo')
    file_data = fields.Binary(string='Archivo Generado', readonly=True)
    state = fields.Selection(
        selection=[('config', 'Configuración'), ('done', 'Listo')],
        default='config',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def _default_report_action_id(self):
        """Reporte por defecto: prioriza nuestro Recibo IPS compacto
        (cabecera MTESS oficial + 2 copias por A4). Si no existe, cae al
        recibo funcionario del l10n_py, y por ultimo al estandar de Odoo."""
        report = self.env['ir.actions.report'].sudo()

        # 1) Nuestro Recibo IPS compacto (preferido)
        ips_report = report.search([
            ('model', '=', 'hr.payslip'),
            ('report_name', '=', 'hr_payslip_bulk_print_cross.report_recibo_ips_a5'),
        ], limit=1)
        if ips_report:
            return ips_report.id

        # 2) Recibo Funcionario de l10n_py (fallback si IPS no esta)
        py_report = report.search([
            ('model', '=', 'hr.payslip'),
            ('report_name', '=', 'l10n_py_hr_payroll_report.report_payslip_funcionario'),
        ], limit=1)
        if py_report:
            return py_report.id

        # 3) Reporte estándar de Odoo
        std_report = report.search([
            ('model', '=', 'hr.payslip'),
            ('report_name', 'in', (
                'hr_payroll.report_payslip',
                'hr_payroll.action_report_payslip',
            )),
        ], limit=1)
        if std_report:
            return std_report.id

        any_report = report.search([('model', '=', 'hr.payslip')], limit=1)
        return any_report.id if any_report else False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []

        payslip_ids = []
        if active_model == 'hr.payslip' and active_ids:
            payslip_ids = active_ids
        elif active_model == 'hr.payslip.run' and active_ids:
            runs = self.env['hr.payslip.run'].browse(active_ids)
            payslip_ids = runs.mapped('slip_ids').ids

        if payslip_ids:
            res['payslip_ids'] = [(6, 0, payslip_ids)]
        return res

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        for rec in self:
            rec.payslip_count = len(rec.payslip_ids)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _filter_payslips(self):
        """Aplica el filtro por estado seleccionado."""
        self.ensure_one()
        slips = self.payslip_ids
        mapping = {
            'all': None,
            'done': ['done', 'paid'],
            'verify': ['verify'],
            'draft_verify_done': ['draft', 'verify', 'done', 'paid'],
        }
        states = mapping.get(self.state_filter)
        if states is not None:
            slips = slips.filtered(lambda s: s.state in states)
        if not slips:
            raise UserError(_(
                'No quedaron recibos para imprimir luego de aplicar el '
                'filtro por estado.'
            ))
        return slips

    def _get_payslip_filename(self, payslip, ext='pdf'):
        """Genera el nombre del archivo individual de un recibo."""
        self.ensure_one()
        emp = payslip.employee_id
        emp_name = _slugify(emp.name) if emp else ''
        emp_doc = _slugify(getattr(emp, 'identification_id', '') or '')
        date_to = payslip.date_to.strftime('%Y_%m') if payslip.date_to else ''
        slip_num = _slugify(payslip.number or str(payslip.id))

        parts = ['Recibo', emp_name]
        if emp_doc:
            parts.append(emp_doc)
        if date_to:
            parts.append(date_to)
        if self.include_payslip_number:
            parts.append(slip_num)
        return f"{'_'.join(p for p in parts if p)}.{ext}"

    def _render_pdf_for_payslip(self, report, payslip):
        """Renderiza el PDF del recibo. Compatible con Odoo 18."""
        # En Odoo 17/18 se usa _render_qweb_pdf con res_ids
        try:
            content, _ext = report.with_context(
                lang=payslip.employee_id.lang or self.env.user.lang or 'es_ES'
            )._render_qweb_pdf(
                report.report_name, res_ids=payslip.ids
            )
        except Exception as e:
            _logger.exception(
                "Error renderizando recibo %s: %s", payslip.display_name, e
            )
            raise UserError(_(
                "Error al generar el PDF del recibo «%s»:\n%s"
            ) % (payslip.display_name, e))
        return content

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def action_generate(self):
        """Genera el archivo (ZIP o PDF único) y lo deja disponible
        para descargar."""
        self.ensure_one()
        if not self.payslip_ids:
            raise UserError(_('Debe seleccionar al menos un recibo de nómina.'))
        if not self.report_action_id:
            raise UserError(_('Debe escoger una plantilla de reporte.'))

        payslips = self._filter_payslips()
        report = self.report_action_id.sudo()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if self.output_mode == 'zip':
            buffer = io.BytesIO()
            used_names = {}
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for slip in payslips:
                    pdf_bytes = self._render_pdf_for_payslip(report, slip)
                    fname = self._get_payslip_filename(slip, ext='pdf')
                    # evitar colisiones
                    if fname in used_names:
                        used_names[fname] += 1
                        base, ext = fname.rsplit('.', 1)
                        fname = f"{base}_{used_names[fname]}.{ext}"
                    else:
                        used_names[fname] = 0
                    zf.writestr(fname, pdf_bytes)
            data = buffer.getvalue()
            buffer.close()
            file_name = f"Recibos_Nomina_{timestamp}.zip"
        else:
            # PDF único: concatenar páginas con PyPDF2 si está disponible,
            # caso contrario rendererizar el reporte en lote (Odoo lo
            # devuelve como un único PDF cuando se le pasan varios res_ids).
            try:
                content, _ext = report._render_qweb_pdf(
                    report.report_name, res_ids=payslips.ids
                )
                data = content
            except Exception as e:
                _logger.exception("Fallo render lote PDF: %s", e)
                raise UserError(_(
                    "No se pudo generar el PDF consolidado:\n%s"
                ) % e)
            file_name = f"Recibos_Nomina_{timestamp}.pdf"

        self.write({
            'file_data': base64.b64encode(data),
            'file_name': file_name,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_download(self):
        """Descarga directa del archivo generado."""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Primero debe generar el archivo.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=%s&id=%s&field=file_data&filename_field=file_name&download=true' % (
                self._name, self.id
            ),
            'target': 'self',
        }
