from odoo import fields, models

class ProductStage(models.Model):
    _name = "product.stage"
    _description = "Etapas de Producto"
    _order = "sequence, name"

    name = fields.Char(string="Etapa", required=True, translate=True)
    sequence = fields.Integer(string="Secuencia", default=1)
    fold = fields.Boolean(string="Doblado en Kanban",
        help="Esta etapa se pliega en la vista Kanban cuando no hay registros en ella.")

