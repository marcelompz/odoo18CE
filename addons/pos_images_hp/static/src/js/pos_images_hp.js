/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/app/models/product_product";

// Patch del modelo ProductProduct para usar image_1920 en lugar de image_128
patch(ProductProduct.prototype, {
    getTemplateImageUrl() {
        // Usar image_1920 directamente - el servidor responderá con la imagen correcta
        return `/web/image?model=product.template&field=image_1920&id=${this.raw.product_tmpl_id}&unique=${this.write_date}`;
    }
});
