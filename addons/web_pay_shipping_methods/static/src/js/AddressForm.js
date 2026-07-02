// Script para manejar formularios de dirección
// Se ejecuta cuando el DOM esté listo

(function() {
    'use strict';
    
    function setupAddressForms() {
        // Verificar si existe nuestro formulario unificado
        const customForm = document.getElementById('register_address_form');
        
        // Verificar si existe el formulario estándar
        const standardForm = document.querySelector('form.js_address_submit');
        
        // Verificar elementos con address_type
        const addressTypeElements = document.querySelectorAll('[name="address_type"]');
        
        // Verificar si estamos en una página de dirección
        const isAddressPage = window.location.pathname.includes('/shop/address') || 
                             window.location.pathname.includes('/shop/checkout');
        
        // Verificar si el usuario es anónimo
        const isAnonymous = !document.querySelector('.o_user_menu') && 
                           !document.querySelector('.o_user_menu_dropdown');
        
        // Buscar todos los formularios que puedan contener campos de contraseña
        const allForms = document.querySelectorAll('form');
        
        allForms.forEach((form, index) => {
            const passwordField = form.querySelector('#register_password, input[name="register_password"]');
            const confirmPasswordField = form.querySelector('#register_confirm_password, input[name="register_confirm_password"]');
            
            if (passwordField || confirmPasswordField) {
                setupPasswordValidation(form);
            }
        });
        
        // Configurar formulario unificado si existe
        if (customForm) {
            setupCustomForm(customForm);
            setupRegisterFormValidation(customForm);
            
            // Agregar listener para verificar si se envía
            customForm.addEventListener('submit', function(e) {
                // Verificar campos específicos
                const nameField = document.getElementById('register_name');
                const emailField = document.getElementById('register_email');
                const passwordField = document.getElementById('register_password');
            });
        }
        
        // Configurar formulario estándar si existe
        if (standardForm) {
            setupStandardForm(standardForm);
        }
    }

    function setupRegisterFormValidation(form) {
        // Agregar validación específica para el formulario de registro
        form.addEventListener('submit', function(e) {
            // Validar contraseñas
            const password = document.getElementById('register_password');
            const confirmPassword = document.getElementById('register_confirm_password');
            
            if (password && confirmPassword) {
                if (password.value !== confirmPassword.value) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    alert('Las contraseñas no coinciden. Por favor, asegúrese de que ambas contraseñas sean iguales.');
                    confirmPassword.focus();
                    return false;
                }
                
                if (password.value.length < 6) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    alert('La contraseña debe tener al menos 6 caracteres.');
                    password.focus();
                    return false;
                }
            }
            
            // Validar campos requeridos
            const requiredFields = form.querySelectorAll('[required]');
            for (let i = 0; i < requiredFields.length; i++) {
                if (!requiredFields[i].value.trim()) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    alert('Por favor complete todos los campos requeridos.');
                    requiredFields[i].focus();
                    return false;
                }
            }
            
            return true;
        });
        
        // Agregar validación en tiempo real para contraseñas
        const password = document.getElementById('register_password');
        const confirmPassword = document.getElementById('register_confirm_password');
        
        if (password && confirmPassword) {
            confirmPassword.addEventListener('input', function() {
                validatePasswordMatch(password, confirmPassword);
            });
            
            password.addEventListener('input', function() {
                validatePasswordMatch(password, confirmPassword);
            });
        }
    }

    function setupPasswordValidation(form) {
        // Agregar validación de contraseñas
        form.addEventListener('submit', (e) => {
            return validatePasswords(e);
        });
        
        // También agregar validación en tiempo real
        const passwordField = form.querySelector('#register_password, input[name="register_password"]');
        const confirmPasswordField = form.querySelector('#register_confirm_password, input[name="register_confirm_password"]');
        
        if (passwordField && confirmPasswordField) {
            confirmPasswordField.addEventListener('input', () => {
                validatePasswordMatch(passwordField, confirmPasswordField);
            });
            
            passwordField.addEventListener('input', () => {
                validatePasswordMatch(passwordField, confirmPasswordField);
            });
        }
    }

    function setupCustomForm(form) {
        // Agregar validación personalizada
        form.addEventListener('submit', (e) => {
            return validateCustomForm(e);
        });
    }

    function setupStandardForm(form) {
        // Agregar validaciones básicas
        const requiredFields = form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', () => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                    field.classList.add('is-valid');
                }
            });
        });
    }

    function validatePasswords(e) {
        const form = e.target;
        const passwordField = form.querySelector('#register_password, input[name="register_password"]');
        const confirmPasswordField = form.querySelector('#register_confirm_password, input[name="register_confirm_password"]');
        
        if (passwordField && confirmPasswordField) {
            const password = passwordField.value;
            const confirmPassword = confirmPasswordField.value;
            
            if (password !== confirmPassword) {
                e.preventDefault();
                e.stopPropagation();
                alert('Las contraseñas no coinciden. Por favor, asegúrese de que ambas contraseñas sean iguales.');
                confirmPasswordField.focus();
                return false;
            }
        }
        
        return true;
    }

    function validatePasswordMatch(passwordField, confirmPasswordField) {
        const password = passwordField.value;
        const confirmPassword = confirmPasswordField.value;
        
        if (confirmPassword && password !== confirmPassword) {
            confirmPasswordField.classList.add('is-invalid');
            confirmPasswordField.classList.remove('is-valid');
        } else if (confirmPassword && password === confirmPassword) {
            confirmPasswordField.classList.remove('is-invalid');
            confirmPasswordField.classList.add('is-valid');
        } else {
            confirmPasswordField.classList.remove('is-invalid', 'is-valid');
        }
    }

    function validateCustomForm(e) {
        // Primero validar contraseñas
        if (!validatePasswords(e)) {
            return false;
        }
        
        // Validar campos requeridos
        const requiredFields = e.target.querySelectorAll('[required]');
        for (let i = 0; i < requiredFields.length; i++) {
            if (!requiredFields[i].value.trim()) {
                e.preventDefault();
                alert('Por favor complete todos los campos requeridos');
                requiredFields[i].focus();
                return false;
            }
        }
        
        return true;
    }
    
    // Ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupAddressForms);
    } else {
        setupAddressForms();
    }
    
    // También ejecutar cuando la ventana se cargue como respaldo
    window.addEventListener('load', setupAddressForms);
    
    // También ejecutar después de un pequeño delay para asegurar que todo esté cargado
    setTimeout(setupAddressForms, 1000);
    
    // Ejecutar múltiples veces para asegurar que se aplique
    setTimeout(setupAddressForms, 2000);
    setTimeout(setupAddressForms, 3000);
    
})(); 