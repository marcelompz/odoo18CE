/** @odoo-module **/

// Código de ejemplo para el demo de pago. No usar imports con @, solo rutas relativas si se requiere.

import publicWidget from "@web/legacy/js/public/public_widget";
// import { jsonrpc } from "@web/core/network/rpc_service";
publicWidget.registry.determine_checkout = publicWidget.Widget.extend({
    selector: '#wrap',
    init() {
        this._super(...arguments);
        // this.rpc = this.bindService("rpc"); // Eliminado para compatibilidad con Odoo 18
    },
    willStart: function () {
        var self = this;
                    this.$el.find('#o_demo_express_checkout_container_6').css('display', 'none')
        return this._super(...arguments);
    },
});