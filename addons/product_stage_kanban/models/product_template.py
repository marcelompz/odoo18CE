from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    stage_id = fields.Many2one(
        "product.stage",
        string="Etapa",
        group_expand="_read_group_stage_ids",
        default=lambda self: self.env["product.stage"].search([], order="sequence", limit=1).id,
        required=True,
        help="Etapa del producto en la vista kanban."
    )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        # Retorna todas las etapas para que sean visibles en el kanban, incluso las vacías
        return self.env['product.stage'].search([])

    def action_open_product_description_wizard(self):
        return {
            "name": "Descripción del Producto",
            "type": "ir.actions.act_window",
            "res_model": "product.description.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_product_id": self.id},
        }

    def action_view_stock_moves(self):
        return {
            "name": "Movimientos de Stock",
            "type": "ir.actions.act_window",
            "res_model": "stock.move",
            "view_mode": "tree,form",
            "domain": [("product_id.product_tmpl_id", "=", self.id)],
        }