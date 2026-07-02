from odoo import fields, models, api


class HrContractTemplate(models.Model):
    _name = 'hr.contract.template'
    _description = 'Plantilla de contrato laboral Paraguay'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(default=10)
    template_code = fields.Selection(
        selection=[
            ('general', 'Modelo General'),
            ('sin_prueba', 'Sin Período de Prueba'),
            ('con_prueba', 'Con Período de Prueba'),
            ('jornal', 'Contrato Jornal'),
            ('comision', 'Contrato Comisión'),
            ('compendio', 'Compendio de Legislación Contractual'),
        ],
        string='Tipo de plantilla',
        required=True,
        default='general',
    )
    description = fields.Html(string='Descripción')
    body_md = fields.Text(string='Contenido (Markdown)', translate=True)
    active = fields.Boolean(default=True)
    available_variables_info = fields.Html(
        string='Variables Disponibles',
        compute='_compute_available_variables_info',
        help='Lista de variables que puedes usar en la plantilla'
    )

    @api.depends()
    def _compute_available_variables_info(self):
        """Genera una guía de variables disponibles para usar en las plantillas"""
        variables_info = """
        <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; font-family: monospace;">
            <h3 style="margin-top: 0;">Variables Disponibles para Plantillas de Contrato</h3>
            <p><strong>Formato:</strong> Usa <code>&lt;&lt;NOMBRE_VARIABLE&gt;&gt;</code> o <code>{{ NOMBRE_VARIABLE }}</code></p>
            
            <h4>📋 Información del Contrato</h4>
            <ul>
                <li><code>CONTRACT_CITY</code> - Ciudad del contrato</li>
                <li><code>CONTRACT_DAY</code> - Día del contrato</li>
                <li><code>CONTRACT_MONTH</code> - Mes del contrato (en palabras)</li>
                <li><code>CONTRACT_YEAR</code> - Año del contrato</li>
            </ul>
            
            <h4>🏢 Información de la Empresa</h4>
            <ul>
                <li><code>COMPANY_NAME</code> - Nombre de la empresa</li>
                <li><code>COMPANY_ADDRESS</code> - Dirección completa de la empresa</li>
                <li><code>COMPANY_REPRESENTATIVE</code> - Representante legal</li>
                <li><code>COMPANY_REPRESENTATIVE_ID</code> - Cédula/RUC del representante</li>
                <li><code>REGISTRO_PATRONAL</code> - Registro patronal</li>
                <li><code>REGISTRO_PATRONAL_IPS</code> - Registro patronal IPS</li>
            </ul>
            
            <h4>👤 Información del Empleado</h4>
            <ul>
                <li><code>EMPLOYEE_NAME</code> o <code>NOMBRE_EMPLEADO</code> - Nombre completo del empleado</li>
                <li><code>TITULO_EMPLEADO</code> - Título (el señor/la señora)</li>
                <li><code>EMPLOYEE_NATIONALITY</code> - Nacionalidad</li>
                <li><code>EMPLOYEE_ID</code> - Cédula de identidad</li>
                <li><code>EMPLOYEE_ADDRESS</code> - Dirección del empleado</li>
                <li><code>GENERO_EMPLEADO</code> - Género (masculino/femenino)</li>
                <li><code>EDAD_EMPLEADO</code> - Estado de edad (mayor/menor de edad)</li>
            </ul>
            
            <h4>💼 Información del Trabajo</h4>
            <ul>
                <li><code>JOB_TITLE</code> - Cargo/Puesto de trabajo</li>
                <li><code>WORK_LOCATION</code> - Lugar de trabajo</li>
                <li><code>SCHEDULE_START</code> - Hora de inicio (ej: 08:00)</li>
                <li><code>SCHEDULE_END</code> - Hora de fin (ej: 17:00)</li>
                <li><code>SCHEDULE_DAYS</code> - Días laborables (ej: lunes a viernes)</li>
                <li><code>SCHEDULE_BREAKS</code> - Horario de descanso (ej: 12:00 a 13:00)</li>
            </ul>
            
            <h4>💰 Información del Salario</h4>
            <ul>
                <li><code>SALARY_AMOUNT</code> - Monto del salario (formateado)</li>
                <li><code>SALARY_AMOUNT_WORDS</code> - Monto en letras</li>
                <li><code>SIMBOLO_MONEDA</code> - Símbolo de la moneda (Gs.)</li>
                <li><code>UNIDAD_MONEDA</code> - Unidad de moneda (guaraní)</li>
                <li><code>SALARY_PAYMENT_DATES</code> - Fechas de pago</li>
                <li><code>SALARY_BANK</code> - Banco para pagos</li>
                <li><code>SALARY_NOTICE_DAYS</code> - Días de preaviso</li>
                <li><code>DAILY_WAGE_AMOUNT</code> - Salario diario (si aplica)</li>
                <li><code>DAILY_WAGE_WORDS</code> - Salario diario en letras</li>
            </ul>
            
            <h4>📅 Otros</h4>
            <ul>
                <li><code>TRIAL_END_DATE</code> - Fecha de fin del período de prueba</li>
                <li><code>JURISDICTION_CITY</code> - Ciudad de jurisdicción</li>
                <li><code>TOOL_ITEM_1</code>, <code>TOOL_ITEM_2</code>, <code>TOOL_ITEM_3</code> - Herramientas/Equipos</li>
                <li><code>TOOLS_SUMMARY</code> - Resumen de herramientas</li>
                <li><code>EXTRA_OBLIGATION_1</code>, <code>EXTRA_OBLIGATION_2</code> - Obligaciones adicionales</li>
                <li><code>COMMISSION_AMOUNT</code> - Monto de comisión (si aplica)</li>
                <li><code>COMMISSION_AMOUNT_WORDS</code> - Comisión en letras</li>
                <li><code>COMMISSION_UNIT</code> - Unidad de comisión</li>
            </ul>
            
            <p style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ccc;">
                <strong>Ejemplo de uso:</strong><br/>
                <code>Entre {{ COMPANY_NAME }} y {{ EMPLOYEE_NAME }}, se acuerda...</code><br/>
                O: <code>Entre &lt;&lt;COMPANY_NAME&gt;&gt; y &lt;&lt;EMPLOYEE_NAME&gt;&gt;, se acuerda...</code>
            </p>
        </div>
        """
        for record in self:
            record.available_variables_info = variables_info


