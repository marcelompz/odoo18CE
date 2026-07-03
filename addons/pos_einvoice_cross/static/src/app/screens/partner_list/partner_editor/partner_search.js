/** @odoo-module */


import {patch} from "@web/core/utils/patch";
import {PartnerDetailsEdit} from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";


patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup(...arguments)
        this.popup = useService("popup");

        // const partner = this.props.partner;
    },

    async searchCustomersRuc() {
        // Verifica si el campo VAT realmente existe en el DOM
        const vatInput = document.querySelector("#vat");
        if (!vatInput) {
            console.error("Campo RUC no encontrado.");
            return;
        }
    
        const ruc = vatInput.value.trim(); // Obtener el valor del campo VAT
    
        // Verifica si el valor del RUC está vacío
        if (!ruc) {
            // Mostrar popup de error si el RUC está vacío
            return this.popup.add(ErrorPopup, {
                title: _t("Mensaje de error"),
                body: _t("Debes ingresar el número de documento"),
            });
        }
    
        try {
            // Llamada a jsonrpc
            const result = await jsonrpc("/web/dataset/call_kw/pos.order/search_customer_by_ruc", {
                model: "pos.order",
                method: "search_customer_by_ruc",
                args: [0],
                kwargs: {
                    ruc: ruc,
                },
            });

            console.log('RESULTADO', result)
    
            // Verificar si se recibió un error en el resultado
            if (result.error) {
                console.error("Error recibido del servidor:", result.error);
                return this.popup.add(ErrorPopup, {
                    title: _t("Error al buscar cliente"),
                    body: result.error,
                });
            }
    
            // Si no hay error, actualizar el campo de nombre y ruc
            const nameField = document.querySelector('input[name=name]');   // campo name
            if (nameField) {
                nameField.value = result.name || "Nombre no disponible"; // Asignar el valor directamente
                nameField.dispatchEvent(new Event('input', { bubbles: true })); // Usar 'input' en vez de 'change'
            }
            
            const vatField = document.querySelector('input[name=vat]');     // campo vat
            if (vatField) {
                vatField.value = result.vat || "Nombre no disponible"; // Asignar el valor directamente
                vatField.dispatchEvent(new Event('input', { bubbles: true })); // Usar 'input' en vez de 'change'
            }
    
            // Actualizar el valor en `this.props.partner`
            this.props.partner.name = result.name || "Nombre no disponible";
            this.render(); // Refrescar el componente
    
        } catch (error) {
            console.error('Error en la consulta:', error);
            return this.popup.add(ErrorPopup, {
                title: _t("Aviso"),
                body: _t("No se pudo completar la búsqueda. Por favor, intenta nuevamente."),
            });
        }
    }
        
})
