from odoo import models, fields, api

class TechnicalInfoQuestion(models.Model):
    _name = 'technical.info.question'
    _description = 'Preguntas de Información Técnica'

    name = fields.Char(
        string='Pregunta',
        required=True,
        translate=True
    )
    recurrent = fields.Boolean(
        string='Pregunta Recurrente',
        default=False,
        help='Si está marcado, esta pregunta se precargará en cada nueva orden de venta'
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de aparición de la pregunta'
    )
    permite_null = fields.Boolean(
        string='Permite Valor Null',
        default=False,
        help='Si está marcado, esta pregunta puede tener un valor null (vacío) en las respuestas'
    )

class SaleOrderTechnicalInfo(models.Model):
    _name = 'sale.order.technical.info'
    _description = 'Información Técnica de Orden de Venta'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        required=True,
        ondelete='cascade'
    )
    question_id = fields.Many2one(
        'technical.info.question',
        string='Pregunta',
        required=True,
        ondelete='restrict'
    )
    answer = fields.Char(
        string='Respuesta'
    )
    permite_null = fields.Boolean(
        related='question_id.permite_null',
        string='Permite Null',
        readonly=True
    )
    sequence = fields.Integer(
        related='question_id.sequence',
        store=True,
        string='Secuencia'
    )
    
    @api.constrains('answer', 'question_id')
    def _check_answer_required(self):
        """Validar que la respuesta sea requerida si la pregunta no permite null"""
        for record in self:
            if record.question_id and not record.question_id.permite_null:
                if not record.answer or not record.answer.strip():
                    raise models.ValidationError(
                        f'La pregunta "{record.question_id.name}" requiere una respuesta.'
                    )
    
    @api.onchange('question_id')
    def _onchange_question_id(self):
        """Limpiar la respuesta cuando cambia la pregunta si es necesario"""
        # La validación de campos requeridos se maneja mediante @api.constrains
        # Si la pregunta permite null, se puede dejar vacío
        # Si no permite null, la validación se encargará de requerirlo

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('default_order_id'):
            # Buscar preguntas recurrentes
            recurrent_questions = self.env['technical.info.question'].search([
                ('recurrent', '=', True)
            ])
            if recurrent_questions:
                # Crear líneas de información técnica
                technical_info_lines = []
                for question in recurrent_questions:
                    technical_info_lines.append((0, 0, {
                        'question_id': question.id,
                        'answer': ''
                    }))
                res['technical_info_ids'] = technical_info_lines
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    technical_info_ids = fields.One2many(
        'sale.order.technical.info',
        'order_id',
        string='Información Técnica'
    )
    technical_notes = fields.Html(
        string='Notas Técnicas',
        default="""
            <table class="table table-bordered">
                <tr>
                    <td style="width: 50%;">Observaciones:</td>
                    <td style="width: 50%;"></td>
                </tr>
                <tr>
                    <td>Recomendaciones:</td>
                    <td></td>
                </tr>
            </table>
        """
    )
    general_description = fields.Html(
        string='Descripción General',
        default="""
            <table class="table table-bordered">
                <tr>
                    <td style="width: 50%;">Diseño:</td>
                    <td style="width: 50%;">Descripción:</td>
                </tr>
                <tr>
                    <td></td>
                    <td>logo:
                        <br>
                        <br>
                        Auspicio delantero
                        <br>
                        <br>
                        Auspicio trasero
                        <br>
                        <br>
                        Auspicio manga derecha
                        <br>
                        <br>
                        Auspicio manga izquierda
                        <br>
                        <br>
                    </td>
                </tr>
                <tr>
                    <td></td>
                    <td></td>
                </tr>
            </table>
        """
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'technical_info_ids' in fields_list:
            # Buscar preguntas recurrentes
            recurrent_questions = self.env['technical.info.question'].search([
                ('recurrent', '=', True)
            ], order='sequence')
            
            # Crear líneas de información técnica
            technical_info_lines = []
            for question in recurrent_questions:
                technical_info_lines.append((0, 0, {
                    'question_id': question.id,
                    'answer': '',
                    'sequence': question.sequence
                }))
            
            res['technical_info_ids'] = technical_info_lines
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('technical_info_ids'):
                # Buscar preguntas recurrentes
                recurrent_questions = self.env['technical.info.question'].search([
                    ('recurrent', '=', True)
                ], order='sequence')
                
                # Crear líneas de información técnica
                technical_info_lines = []
                for question in recurrent_questions:
                    technical_info_lines.append((0, 0, {
                        'question_id': question.id,
                        'answer': '',
                        'sequence': question.sequence
                    }))
                
                vals['technical_info_ids'] = technical_info_lines
        return super().create(vals_list) 