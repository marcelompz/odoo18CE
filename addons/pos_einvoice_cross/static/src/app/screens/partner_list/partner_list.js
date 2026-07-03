/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { session } from "@web/session";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";

class CustomPartnerListScreen extends PartnerList {
    static components = { PartnerDetailsEdit, PartnerLine };
    static template = "point_of_sale.PartnerList";

    setup() {
        super.setup();
        // Aquí puedes agregar tu lógica adicional, si es necesario
    }

    createPartner() {
        // Llamamos a la implementación original de createPartner
        super.createPartner();

        // Asignar ciudad por defecto cuando se crea un nuevo partner
        const { city_id } = this.pos.company;  // Accediendo a la ciudad desde la configuración de la empresa
        if (this.state.editModeProps.partner) {
            this.state.editModeProps.partner.city_id = city_id || null;  // Asignar city_id si existe
        }

        console.log("City ID assigned to new partner:", this.state.editModeProps.partner.city_id);
    }

    async saveChanges(processedChanges) {
        // Modificar la lógica de guardar cambios si es necesario
        const partnerId = await this.orm.call("res.partner", "create_from_ui", [processedChanges]);
        await this.pos._loadPartners([partnerId]);
        this.state.selectedPartner = this.pos.db.get_partner_by_id(partnerId);
        this.confirm();
    }

    async getNewPartners() {
        let domain = [];
        const limit = 30;
        if (this.state.query) {
            const search_fields = ["name", "parent_name", "phone_mobile_search", "email", "vat"]; // Añadimos "vat"
            domain = [
                ...Array(search_fields.length - 1).fill('|'),
                ...search_fields.map(field => [field, "ilike", this.state.query + "%"])
            ];
        }
        // FIXME POSREF timeout
        const result = await this.orm.silent.call(
            "pos.session",
            "get_pos_ui_res_partner_by_params",
            [[odoo.pos_session_id], { domain, limit: limit, offset: this.state.currentOffset }]
        );
        return result;
    }
}

registry.category("pos_screens").add("CustomPartnerListScreen", CustomPartnerListScreen);
