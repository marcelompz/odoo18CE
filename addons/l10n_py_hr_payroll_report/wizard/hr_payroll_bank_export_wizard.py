from odoo import api, fields, models, _
from odoo.exceptions import UserError

import base64
import io

try:
    import xlsxwriter
except ImportError:  # pragma: no cover
    xlsxwriter = None


class HrPayrollBankExportWizard(models.TransientModel):
    _name = 'hr.payroll.bank.export.wizard'
    _description = 'Exportación bancaria de nómina (Excel)'

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lote de nómina', required=False)
    payment_date = fields.Date(string='Fecha a pagar', required=True, default=fields.Date.context_today)
    concept = fields.Char(string='Concepto', required=True, default='ACREDITACION')
    debit_account = fields.Char(string='Cuenta débito', required=True, default=lambda self: self._default_debit_account())
    bank_client = fields.Char(string='Banco cliente', required=True, default='Itau')
    payment_type = fields.Char(string='Tipo de pago', required=True, default='Credito en cuenta')
    currency = fields.Char(string='Moneda', required=True, default='Guaranies')
    comment = fields.Char(string='Comentario')
    reference = fields.Char(string='Referencia operación')
    file_data = fields.Binary(string='Archivo', readonly=True)
    filename = fields.Char(readonly=True)

    def _default_debit_account(self):
        company = self.env.company
        bank = company.partner_id.bank_ids[:1]
        return bank.acc_number if bank else ''

    def action_generate_file(self):
        self.ensure_one()
        if not self.payslip_run_id:
            raise UserError(_("Selecciona un lote de nómina."))
        if xlsxwriter is None:
            raise UserError(_("El módulo python 'xlsxwriter' no está instalado. Instálalo en el servidor para generar la planilla."))

        payslips = self.payslip_run_id.slip_ids.filtered(lambda s: s.state in ('done', 'paid'))
        if not payslips:
            raise UserError(_("El lote no tiene recibos en estado 'Hecho' o 'Pagado'."))

        missing_accounts = payslips.filtered(lambda s: not s.employee_id.bank_account_id or not s.employee_id.bank_account_id.acc_number)
        if missing_accounts:
            raise UserError(_("Faltan cuentas bancarias para: %s") % ', '.join(missing_accounts.mapped('employee_id.name')))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Pagos')

        headers = [
            _('Concepto'),
            _('Cuenta débito'),
            _('Banco cliente'),
            _('Cuenta crédito'),
            _('Fecha a pagar'),
            _('Tipo de pago'),
            _('Beneficiario'),
            _('Moneda'),
            _('Monto del pago'),
            _('Nro. documento beneficiario'),
            _('Comentario'),
            _('Referencia operación'),
        ]
        header_format = workbook.add_format({'bold': True, 'bg_color': '#EEEEEE'})
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        date_str = fields.Date.to_string(self.payment_date)

        for row, slip in enumerate(payslips, start=1):
            employee = slip.employee_id
            bank_account = employee.bank_account_id
            worksheet.write(row, 0, self.concept or '')
            worksheet.write(row, 1, self.debit_account or '')
            worksheet.write(row, 2, self.bank_client or '')
            worksheet.write(row, 3, bank_account.acc_number or '')
            worksheet.write(row, 4, date_str or '')
            worksheet.write(row, 5, self.payment_type or '')
            worksheet.write(row, 6, employee.name or '')
            worksheet.write(row, 7, self.currency or '')
            worksheet.write_number(row, 8, slip.get_total_cobrar() or 0.0)
            worksheet.write(row, 9, employee.identification_id or '')
            worksheet.write(row, 10, self.comment or '')
            worksheet.write(row, 11, self.reference or slip.number or '')

        workbook.close()
        output.seek(0)
        filename = 'Pagos_Banco_%s.xlsx' % (self.payslip_run_id.name or 'lote')
        file_data = base64.b64encode(output.read())
        
        # Crear un attachment para descargar el archivo
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': file_data,
            'res_model': 'hr.payroll.bank.export.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        # Retornar acción de descarga del attachment
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

