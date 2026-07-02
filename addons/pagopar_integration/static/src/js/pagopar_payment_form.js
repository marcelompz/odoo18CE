/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import PaymentForm from "@payment/js/payment_form";

    // Extend the payment form to handle Pagopar specifics
    PaymentForm.include({

        /**
         * @override
         */
        _onClickPayButton: function (ev) {
            if ($(ev.currentTarget).find('input[name="provider_code"]').val() === 'pagopar') {
                this._processPagoparPayment(ev);
            } else {
                return this._super.apply(this, arguments);
            }
        },

        /**
         * Process Pagopar payment
         * @private
         * @param {Event} ev
         */
        _processPagoparPayment: function (ev) {
            ev.preventDefault();
            var $form = $(ev.currentTarget).closest('form');
            var $button = $(ev.currentTarget);
            
            // Disable the button to prevent double submission
            $button.prop('disabled', true);
            $button.find('.fa').removeClass('fa-lock').addClass('fa-spinner fa-spin');
            
            // Show loading message
            this._showPagoparLoading();
            
            // Submit the form
            var formData = new FormData($form[0]);
            
            $.ajax({
                url: $form.attr('action') || '/payment/transaction',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(result) {
                    if (result.pagopar_payment_url) {
                        // Redirect to Pagopar payment page
                        window.location.href = result.pagopar_payment_url;
                    } else if (result.error) {
                        this._showPagoparError(result.error);
                        this._resetPagoparButton($button);
                    } else {
                        // Handle other success scenarios
                        if (result.redirect_url) {
                            window.location.href = result.redirect_url;
                        } else {
                            this._showPagoparError(_t('Error inesperado al procesar el pago'));
                            this._resetPagoparButton($button);
                        }
                    }
                }.bind(this),
                error: function(xhr, status, error) {
                    this._showPagoparError(_t('Error de conexión: ') + error);
                    this._resetPagoparButton($button);
                }.bind(this)
            });
        },

        /**
         * Show Pagopar loading message
         * @private
         */
        _showPagoparLoading: function () {
            var $alert = $('<div class="alert alert-info pagopar-alert">' +
                '<i class="fa fa-spinner fa-spin"></i> ' +
                _t('Conectando con Pagopar...') +
                '</div>');
            this._removePagoparAlerts();
            this.$el.prepend($alert);
        },

        /**
         * Show Pagopar error message
         * @private
         * @param {string} message
         */
        _showPagoparError: function (message) {
            var $alert = $('<div class="alert alert-danger pagopar-alert">' +
                '<i class="fa fa-exclamation-triangle"></i> ' +
                '<strong>' + _t('Error de Pagopar: ') + '</strong>' + message +
                '</div>');
            this._removePagoparAlerts();
            this.$el.prepend($alert);
        },

        /**
         * Remove all Pagopar alert messages
         * @private
         */
        _removePagoparAlerts: function () {
            this.$el.find('.pagopar-alert').remove();
        },

        /**
         * Reset Pagopar payment button
         * @private
         * @param {jQuery} $button
         */
        _resetPagoparButton: function ($button) {
            $button.prop('disabled', false);
            $button.find('.fa').removeClass('fa-spinner fa-spin').addClass('fa-lock');
        },

    });

    // Widget for Pagopar payment status checking
    publicWidget.registry.PagoparStatusChecker = publicWidget.Widget.extend({
        selector: '.pagopar-status-checker',
        events: {
            'click .btn-check-status': '_onCheckStatus',
        },

        /**
         * Check payment status
         * @private
         * @param {Event} ev
         */
        _onCheckStatus: function (ev) {
            ev.preventDefault();
            var $button = $(ev.currentTarget);
            var orderId = $button.data('order-id');
            
            if (!orderId) {
                this._showMessage('error', _t('ID de orden no encontrado'));
                return;
            }

            $button.prop('disabled', true);
            $button.find('.fa').removeClass('fa-refresh').addClass('fa-spinner fa-spin');

            $.ajax({
                url: '/payment/pagopar/validate',
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {order_id: orderId}
                }),
                success: function(result) {
                    if (result.result && result.result.success) {
                        if (result.result.status === 'done') {
                            this._showMessage('success', _t('¡Pago confirmado! Recargando página...'));
                            setTimeout(function() {
                                location.reload();
                            }, 2000);
                        } else if (result.result.status === 'pending') {
                            this._showMessage('warning', _t('El pago aún está pendiente'));
                        } else {
                            this._showMessage('info', _t('Estado del pago: ') + result.result.status);
                        }
                    } else {
                        var error = result.result ? result.result.error : _t('Error desconocido');
                        this._showMessage('error', _t('Error al verificar estado: ') + error);
                    }
                    this._resetButton($button);
                }.bind(this),
                error: function() {
                    this._showMessage('error', _t('Error de conexión al verificar el estado'));
                    this._resetButton($button);
                }.bind(this)
            });
        },

        /**
         * Show message to user
         * @private
         * @param {string} type
         * @param {string} message
         */
        _showMessage: function (type, message) {
            var alertClass = 'alert-info';
            if (type === 'success') alertClass = 'alert-success';
            else if (type === 'error') alertClass = 'alert-danger';
            else if (type === 'warning') alertClass = 'alert-warning';

            var $alert = $('<div class="alert ' + alertClass + ' alert-dismissible">' +
                '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
                message +
                '</div>');
            
            this.$el.find('.alert').remove();
            this.$el.prepend($alert);
            
            // Auto-hide after 5 seconds
            setTimeout(function() {
                $alert.fadeOut();
            }, 5000);
        },

        /**
         * Reset button state
         * @private
         * @param {jQuery} $button
         */
        _resetButton: function ($button) {
            $button.prop('disabled', false);
            $button.find('.fa').removeClass('fa-spinner fa-spin').addClass('fa-refresh');
        },
    });

    // Widget for Pagopar payment widget selection
    publicWidget.registry.PagoparPaymentWidget = publicWidget.Widget.extend({
        selector: '.pagopar-payment-widget',
        events: {
            'click': '_onSelectPaymentMethod',
        },

        /**
         * Select this payment method
         * @private
         * @param {Event} ev
         */
        _onSelectPaymentMethod: function (ev) {
            ev.preventDefault();
            
            // Remove selection from other widgets
            $('.pagopar-payment-widget').removeClass('selected');
            
            // Add selection to this widget
            this.$el.addClass('selected');
            
            // Update hidden form fields if present
            $('input[name="payment_provider"]').val('pagopar');
            $('input[name="provider_code"]').val('pagopar');
            
            // Trigger custom event
            this.$el.trigger('pagopar:payment_method_selected', ['pagopar']);
        },

    });

    // Widget for checkout process
    publicWidget.registry.PagoparCheckout = publicWidget.Widget.extend({
        selector: '.checkout-pagopar',
        events: {
            'click .btn-process-payment': '_onProcessPayment',
            'change input[name="payment_method"]': '_onPaymentMethodChange',
        },

        /**
         * Process payment button clicked
         * @private
         * @param {Event} ev
         */
        _onProcessPayment: function (ev) {
            ev.preventDefault();
            var $button = $(ev.currentTarget);
            
            // Validate selection
            if (!$('input[name="payment_method"]:checked').length) {
                this._showAlert('warning', _t('Por favor seleccione un método de pago'));
                return;
            }
            
            // Show loading state
            this._setLoadingState($button, true);
            
            // Get form data
            var formData = this._getCheckoutData();
            
            // Process the payment
            this._submitPayment(formData, $button);
        },

        /**
         * Payment method selection changed
         * @private
         * @param {Event} ev
         */
        _onPaymentMethodChange: function (ev) {
            var selectedMethod = $(ev.currentTarget).val();
            
            // Update UI based on selected method
            this._updatePaymentMethodUI(selectedMethod);
        },

        /**
         * Get checkout form data
         * @private
         * @returns {Object}
         */
        _getCheckoutData: function () {
            return {
                payment_method: $('input[name="payment_method"]:checked').val(),
                provider_id: $('input[name="provider_id"]').val(),
                order_id: $('input[name="order_id"]').val(),
                amount: $('input[name="amount"]').val(),
                currency: $('input[name="currency"]').val(),
                csrf_token: $('input[name="csrf_token"]').val(),
            };
        },

        /**
         * Submit payment data
         * @private
         * @param {Object} data
         * @param {jQuery} $button
         */
        _submitPayment: function (data, $button) {
            $.ajax({
                url: '/shop/payment/transaction',
                type: 'POST',
                data: data,
                success: function(result) {
                    if (result.success && result.transaction_id) {
                        // Redirect to payment processing
                        window.location.href = '/payment/pagopar/payment_form?tx_id=' + result.transaction_id;
                    } else {
                        this._showAlert('danger', result.error || _t('Error al crear la transacción'));
                        this._setLoadingState($button, false);
                    }
                }.bind(this),
                error: function(xhr, status, error) {
                    this._showAlert('danger', _t('Error de conexión: ') + error);
                    this._setLoadingState($button, false);
                }.bind(this)
            });
        },

        /**
         * Update payment method UI
         * @private
         * @param {string} method
         */
        _updatePaymentMethodUI: function (method) {
            // Update visual feedback
            $('.payment-method-info').hide();
            $('.payment-method-info[data-method="' + method + '"]').show();
            
            // Update security information
            this._updateSecurityInfo(method);
        },

        /**
         * Update security information display
         * @private
         * @param {string} method
         */
        _updateSecurityInfo: function (method) {
            var securityText = '';
            if (method === 'pagopar') {
                securityText = _t('Procesado de forma segura por Pagopar con encriptación SSL');
            }
            $('.security-info-text').text(securityText);
        },

        /**
         * Set loading state for button
         * @private
         * @param {jQuery} $button
         * @param {boolean} loading
         */
        _setLoadingState: function ($button, loading) {
            if (loading) {
                $button.prop('disabled', true);
                $button.find('.fa').removeClass('fa-lock').addClass('fa-spinner fa-spin');
                $button.find('.btn-text').text(_t('Procesando...'));
            } else {
                $button.prop('disabled', false);
                $button.find('.fa').removeClass('fa-spinner fa-spin').addClass('fa-lock');
                $button.find('.btn-text').text(_t('Proceder al Pago Seguro'));
            }
        },

        /**
         * Show alert message
         * @private
         * @param {string} type
         * @param {string} message
         */
        _showAlert: function (type, message) {
            var $alert = $('<div class="alert alert-' + type + ' alert-dismissible">' +
                '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
                '<i class="fa fa-exclamation-triangle"></i> ' + message +
                '</div>');
            
            this.$el.find('.alert').remove();
            this.$el.prepend($alert);
            
            // Auto-dismiss after 5 seconds
            setTimeout(function() {
                $alert.fadeOut();
            }, 5000);
        },

    });

    // Widget for portal payment filters
    publicWidget.registry.PagoparPortalFilters = publicWidget.Widget.extend({
        selector: '.payment-controls',
        events: {
            'click .filter-btn': '_onFilterClick',
            'click .sort-btn': '_onSortClick',
        },

        /**
         * Filter button clicked
         * @private
         * @param {Event} ev
         */
        _onFilterClick: function (ev) {
            ev.preventDefault();
            var $button = $(ev.currentTarget);
            var filterValue = $button.data('filter');
            
            // Update active state
            $('.filter-btn').removeClass('active');
            $button.addClass('active');
            
            // Apply filter
            this._applyFilter(filterValue);
        },

        /**
         * Sort button clicked
         * @private
         * @param {Event} ev
         */
        _onSortClick: function (ev) {
            ev.preventDefault();
            var $button = $(ev.currentTarget);
            var sortValue = $button.data('sort');
            
            // Update active state
            $('.sort-btn').removeClass('active');
            $button.addClass('active');
            
            // Apply sorting
            this._applySort(sortValue);
        },

        /**
         * Apply filter to table
         * @private
         * @param {string} filter
         */
        _applyFilter: function (filter) {
            var $rows = $('tbody tr');
            
            if (filter === 'all') {
                $rows.show();
            } else {
                $rows.each(function() {
                    var $row = $(this);
                    var status = $row.find('.badge').text().toLowerCase();
                    
                    if (status.includes(filter)) {
                        $row.show();
                    } else {
                        $row.hide();
                    }
                });
            }
            
            this._updateNoResultsMessage();
        },

        /**
         * Apply sorting to table
         * @private
         * @param {string} sort
         */
        _applySort: function (sort) {
            var $tbody = $('tbody');
            var $rows = $tbody.find('tr').get();
            
            $rows.sort(function(a, b) {
                var aValue, bValue;
                
                switch(sort) {
                    case 'date':
                        aValue = new Date($(a).find('td:nth-child(2)').text());
                        bValue = new Date($(b).find('td:nth-child(2)').text());
                        return bValue - aValue; // Newest first
                    case 'amount':
                        aValue = parseFloat($(a).find('td:nth-child(3)').text().replace(/[^\d.]/g, ''));
                        bValue = parseFloat($(b).find('td:nth-child(3)').text().replace(/[^\d.]/g, ''));
                        return bValue - aValue; // Highest first
                    case 'reference':
                        aValue = $(a).find('td:first-child').text().toLowerCase();
                        bValue = $(b).find('td:first-child').text().toLowerCase();
                        return aValue.localeCompare(bValue);
                    default:
                        return 0;
                }
            });
            
            $tbody.append($rows);
        },

        /**
         * Update no results message
         * @private
         */
        _updateNoResultsMessage: function () {
            var $visibleRows = $('tbody tr:visible');
            var $noResultsRow = $('tbody .no-results-row');
            
            if ($visibleRows.length === 0) {
                if ($noResultsRow.length === 0) {
                    $('tbody').append(
                        '<tr class="no-results-row"><td colspan="6" class="text-center text-muted">' +
                        '<i class="fa fa-search fa-2x mb-2"></i><br/>' +
                        _t('No se encontraron pagos con los filtros seleccionados') +
                        '</td></tr>'
                    );
                }
            } else {
                $noResultsRow.remove();
            }
        },

    });

    // Initialize portal home counter
    publicWidget.registry.PagoparPortalCounter = publicWidget.Widget.extend({
        selector: '.o_portal_my_home',

        /**
         * Widget start
         */
        start: function () {
            this._super.apply(this, arguments);
            this._updatePaymentCounter();
        },

        /**
         * Update payment counter
         * @private
         */
        _updatePaymentCounter: function () {
            var self = this;
            
            $.ajax({
                url: '/my/payments/count',
                type: 'GET',
                success: function(result) {
                    if (result.count !== undefined) {
                        var $counter = self.$el.find('.pagopar-payment-count');
                        if ($counter.length) {
                            $counter.text(result.count);
                        }
                    }
                }.bind(this),
                error: function() {
                    // Silently fail
                }
            });
        },

    }); 