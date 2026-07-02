odoo.define('web_checkout_simplifier.checkout_simplifier', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    publicWidget.registry.CheckoutSimplifier = publicWidget.Widget.extend({
        selector: '#simplified_checkout_form',
        events: {
            'change input[name="payment_method"]': '_onPaymentMethodChange',
            'change select[name="country_id"]': '_onCountryChange',
            'submit': '_onFormSubmit',
            'change input[name="checkout_file"]': '_onFileChange'
        },

        /**
         * Inicialización del widget
         */
        start: function () {
            this._super.apply(this, arguments);
            this._initializeForm();
            return this._super.apply(this, arguments);
        },

        /**
         * Inicializa el formulario con valores por defecto
         */
        _initializeForm: function () {
            // Cargar estados si hay un país seleccionado (incluyendo Paraguay por defecto)
            var countryId = this.$('select[name="country_id"]').val();
            if (countryId) {
                this._loadStates(countryId);
            }

            // Verificar método de pago seleccionado
            var selectedPayment = this.$('input[name="payment_method"]:checked');
            if (selectedPayment.length) {
                this._toggleBankTransferSection(selectedPayment.data('code'));
            }
            
            // Mostrar mensaje informativo sobre comprobantes
            this._showPaymentProofInfo();
        },

        /**
         * Muestra información sobre comprobantes de pago
         */
        _showPaymentProofInfo: function () {
            // Agregar tooltip o información adicional sobre comprobantes
            var fileInput = this.$('input[name="checkout_file"]');
            if (fileInput.length) {
                fileInput.on('focus', function() {
                    $(this).siblings('.form-text').addClass('text-primary');
                }).on('blur', function() {
                    $(this).siblings('.form-text').removeClass('text-primary');
                });
            }
        },

        /**
         * Maneja el cambio de método de pago
         */
        _onPaymentMethodChange: function (ev) {
            var paymentCode = $(ev.currentTarget).data('code');
            this._toggleBankTransferSection(paymentCode);
            
            // Obtener información adicional del método de pago
            var paymentMethodId = $(ev.currentTarget).val();
            this._getPaymentInfo(paymentMethodId);
        },

        /**
         * Muestra u oculta la sección de transferencia bancaria
         */
        _toggleBankTransferSection: function (paymentCode) {
            var bankTransferSection = $('#bank_transfer_section');
            
            if (paymentCode === 'transfer') {
                bankTransferSection.slideDown(300);
                this._showBankTransferMessage();
            } else {
                bankTransferSection.slideUp(300);
            }
        },

        /**
         * Muestra mensaje específico de transferencia bancaria
         */
        _showBankTransferMessage: function () {
            // Agregar animación y efectos visuales
            var alertBox = $('#bank_transfer_section .alert');
            alertBox.addClass('animate__animated animate__fadeIn');
            
            // Opcional: agregar sonido de notificación (si está disponible)
            if (typeof Audio !== 'undefined') {
                try {
                    var audio = new Audio('/web/static/src/audio/ting.ogg');
                    audio.volume = 0.3;
                    audio.play().catch(function() {
                        // Ignorar errores de audio
                    });
                } catch (e) {
                    // Ignorar errores de audio
                }
            }
        },

        /**
         * Obtiene información adicional del método de pago
         */
        _getPaymentInfo: function (paymentMethodId) {
            var self = this;
            
            ajax.jsonRpc('/shop/checkout/get_payment_info', 'call', {
                'payment_method_id': paymentMethodId
            }).then(function (result) {
                if (result.is_transfer) {
                    // Actualizar instrucciones específicas si están disponibles
                    if (result.instructions) {
                        var instructionsContainer = $('#bank_transfer_section .alert p');
                        if (instructionsContainer.length) {
                            instructionsContainer.html(result.instructions);
                        }
                    }
                }
            }).catch(function (error) {
                console.warn('Error al obtener información del método de pago:', error);
            });
        },

        /**
         * Maneja el cambio de país
         */
        _onCountryChange: function (ev) {
            var countryId = $(ev.currentTarget).val();
            this._loadStates(countryId);
        },

        /**
         * Carga los estados de un país específico
         */
        _loadStates: function (countryId) {
            var self = this;
            var stateSelect = this.$('select[name="state_id"]');
            
            if (!countryId) {
                stateSelect.empty().append('<option value="">Seleccionar estado...</option>');
                return;
            }

            // Mostrar loading
            stateSelect.prop('disabled', true);
            stateSelect.empty().append('<option value="">Cargando estados...</option>');

            ajax.jsonRpc('/shop/checkout/get_states', 'call', {
                'country_id': countryId
            }).then(function (states) {
                stateSelect.empty();
                stateSelect.append('<option value="">Seleccionar estado...</option>');
                
                states.forEach(function (state) {
                    stateSelect.append(
                        $('<option></option>')
                            .attr('value', state.id)
                            .text(state.name)
                    );
                });
                
                stateSelect.prop('disabled', false);
            }).catch(function (error) {
                console.error('Error al cargar estados:', error);
                stateSelect.empty().append('<option value="">Error al cargar estados</option>');
                stateSelect.prop('disabled', false);
            });
        },

        /**
         * Valida el archivo seleccionado
         */
        _onFileChange: function (ev) {
            var file = ev.target.files[0];
            var fileInput = $(ev.currentTarget);
            var maxSize = 10 * 1024 * 1024; // 10MB
            var allowedTypes = [
                'application/pdf',
                'image/jpeg',
                'image/jpg', 
                'image/png',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain'
            ];

            if (file) {
                // Validar tamaño
                if (file.size > maxSize) {
                    this._showFileError('El archivo es demasiado grande. Tamaño máximo: 10MB');
                    fileInput.val('');
                    return;
                }

                // Validar tipo
                if (!allowedTypes.includes(file.type)) {
                    this._showFileError('Tipo de archivo no permitido. Use: PDF, JPG, PNG, DOC, DOCX, TXT');
                    fileInput.val('');
                    return;
                }

                // Mostrar información del archivo
                this._showFileInfo(file);
            }
        },

        /**
         * Muestra error de archivo
         */
        _showFileError: function (message) {
            var fileInput = this.$('input[name="checkout_file"]');
            var errorDiv = fileInput.siblings('.file-error');
            
            if (errorDiv.length === 0) {
                errorDiv = $('<div class="file-error text-danger small mt-1"></div>');
                fileInput.after(errorDiv);
            }
            
            errorDiv.text(message).show();
            
            // Ocultar después de 5 segundos
            setTimeout(function () {
                errorDiv.fadeOut();
            }, 5000);
        },

        /**
         * Muestra información del archivo seleccionado
         */
        _showFileInfo: function (file) {
            var fileInput = this.$('input[name="checkout_file"]');
            var infoDiv = fileInput.siblings('.file-info');
            
            if (infoDiv.length === 0) {
                infoDiv = $('<div class="file-info text-success small mt-1"></div>');
                fileInput.after(infoDiv);
            }
            
            var sizeText = this._formatFileSize(file.size);
            infoDiv.html('<i class="fa fa-check-circle me-1"></i>Comprobante seleccionado: ' + file.name + ' (' + sizeText + ')').show();
            
            // Agregar mensaje adicional para transferencias bancarias
            var selectedPayment = this.$('input[name="payment_method"]:checked');
            if (selectedPayment.length && selectedPayment.data('code') === 'transfer') {
                var extraInfo = $('<div class="file-extra-info text-info small mt-1"></div>');
                extraInfo.html('<i class="fa fa-info-circle me-1"></i>Este comprobante se guardará como comentario en su pedido.');
                infoDiv.after(extraInfo);
            }
        },

        /**
         * Formatea el tamaño del archivo
         */
        _formatFileSize: function (bytes) {
            if (bytes === 0) return '0 Bytes';
            var k = 1024;
            var sizes = ['Bytes', 'KB', 'MB', 'GB'];
            var i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        /**
         * Valida el formulario antes del envío
         */
        _onFormSubmit: function (ev) {
            var isValid = this._validateForm();
            
            if (!isValid) {
                ev.preventDefault();
                return false;
            }

            // Mostrar loading en el botón
            var submitBtn = this.$('button[type="submit"]');
            var originalText = submitBtn.html();
            submitBtn.prop('disabled', true);
            submitBtn.html('<i class="fa fa-spinner fa-spin me-2"></i>Procesando...');

            // Restaurar botón si hay error (después de un tiempo)
            setTimeout(function () {
                submitBtn.prop('disabled', false);
                submitBtn.html(originalText);
            }, 10000);
        },

        /**
         * Valida todos los campos del formulario
         */
        _validateForm: function () {
            var isValid = true;
            var firstErrorField = null;

            // Limpiar errores previos
            this.$('.is-invalid').removeClass('is-invalid');
            this.$('.custom-error').remove();

            // Validar campos requeridos
            var requiredFields = [
                'name', 'email', 'street', 'city', 'country_id'
            ];

            requiredFields.forEach(function (fieldName) {
                var field = this.$('[name="' + fieldName + '"]');
                var value = field.val();
                
                if (!value || value.trim() === '') {
                    this._showFieldError(field, 'Este campo es requerido');
                    isValid = false;
                    if (!firstErrorField) firstErrorField = field;
                }
            }.bind(this));

            // Validar email
            var emailField = this.$('[name="email"]');
            var emailValue = emailField.val();
            if (emailValue && !this._isValidEmail(emailValue)) {
                this._showFieldError(emailField, 'Ingrese un email válido');
                isValid = false;
                if (!firstErrorField) firstErrorField = emailField;
            }

            // Validar método de pago
            var paymentMethod = this.$('input[name="payment_method"]:checked');
            if (paymentMethod.length === 0) {
                this._showFieldError(this.$('input[name="payment_method"]').first(), 'Debe seleccionar un método de pago');
                isValid = false;
                if (!firstErrorField) firstErrorField = this.$('input[name="payment_method"]').first();
            }

            // Scroll al primer error
            if (!isValid && firstErrorField) {
                $('html, body').animate({
                    scrollTop: firstErrorField.offset().top - 100
                }, 500);
                firstErrorField.focus();
            }

            return isValid;
        },

        /**
         * Muestra error en un campo específico
         */
        _showFieldError: function (field, message) {
            field.addClass('is-invalid');
            var errorDiv = $('<div class="custom-error invalid-feedback d-block">' + message + '</div>');
            field.after(errorDiv);
        },

        /**
         * Valida formato de email
         */
        _isValidEmail: function (email) {
            var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        }
    });

    // Inicializar cuando el DOM esté listo
    $(document).ready(function () {
        // Agregar estilos CSS adicionales dinámicamente
        var additionalCSS = `
            <style>
                .animate__animated {
                    animation-duration: 0.5s;
                    animation-fill-mode: both;
                }
                
                .animate__fadeIn {
                    animation-name: fadeIn;
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                
                .form-check:hover {
                    background-color: #f8f9fa;
                    transition: background-color 0.2s ease;
                }
                
                .form-check-input:checked + .form-check-label {
                    color: #0d6efd;
                    font-weight: 500;
                }
                
                .btn-primary:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    transition: all 0.2s ease;
                }
                
                .card {
                    transition: box-shadow 0.3s ease;
                }
                
                .card:hover {
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                }
                
                .file-info, .file-error {
                    animation: slideDown 0.3s ease;
                }
                
                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            </style>
        `;
        
        $('head').append(additionalCSS);
    });

    return publicWidget.registry.CheckoutSimplifier;
});

