/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.address_modal_checkout = publicWidget.Widget.extend({
    selector: '.oe_cart', // O el selector principal de tu checkout

    events: {
        'click .js_open_address_modal': '_onOpenAddressModal',
        'submit #address_modal_form': '_onSubmitAddressForm',
    },

    _onOpenAddressModal: function (ev) {
        ev.preventDefault();
        var addressId = $(ev.currentTarget).data('address-id') || '';
        var addressType = $(ev.currentTarget).data('address-type') || 'billing';
        $('#address_modal_form').data('address-type', addressType);
        if (addressId) {
            // Cargar datos por AJAX
            $.get('/one_page_checkout/get_address', { address_id: addressId }, function(data) {
                $('#modal_name').val(data.name || '');
                $('#modal_street').val(data.street || '');
                $('#modal_city').val(data.city || '');
                $('#modal_zip').val(data.zip || '');
                $('#modal_phone').val(data.phone || '');
                $('#modal_address_id').val(addressId);
                $('#addressModal').modal('show');
                // Precargar país y estado al editar
                // loadCountriesAndStates(data.country_id, data.state_id); // Eliminado
            });
        } else {
            $('#address_modal_form')[0].reset();
            $('#modal_address_id').val('');
            $('#addressModal').modal('show');
            // Llenar selects al crear nueva dirección
            // loadCountriesAndStates(null, null); // Eliminado
        }
    },

    _onSubmitAddressForm: function (ev) {
        ev.preventDefault();
        var formData = $(ev.currentTarget).serializeArray();
        var data = {};
        formData.forEach(function (item) {
            data[item.name] = item.value;
        });
        data['address_type'] = $('#address_modal_form').data('address-type');
        $.post('/one_page_checkout/save_address', data, function(response) {
            if (response.success) {
                $('#addressModal').modal('hide');
                location.reload();
            } else {
                alert(response.error || 'Error al guardar la dirección');
            }
        }, 'json');
    },
});

$(document).on('click', '.js_open_address_modal', function (e) {
    if (window.isPublicUser) {
        window.location.href = '/web/signup';
        return false;
    }
    // ... aquí va el resto de tu lógica para abrir el modal ...
});

