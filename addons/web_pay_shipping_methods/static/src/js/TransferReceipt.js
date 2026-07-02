// Script simple para manejar la subida de comprobantes de transferencia
document.addEventListener('DOMContentLoaded', function() {
    // Función para asegurar que el formulario tenga enctype
    function ensureFormEnctype() {
        var fileInput = document.getElementById('transfer_receipt_file');
        if (fileInput) {
            var form = fileInput.closest('form');
            if (form) {
                form.setAttribute('enctype', 'multipart/form-data');
            }
        }
    }
    
    // Función para enviar archivo al servidor
    function uploadFileToServer(file) {
        var formData = new FormData();
        formData.append('bank_transfer_receipt', file);
        
        fetch('/shop/store_transfer_receipt', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showMessage('Archivo enviado correctamente', 'success');
            } else {
                console.error('Error al enviar archivo:', data.message);
                showMessage('Error al enviar archivo: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error en la petición:', error);
            showMessage('Error al enviar archivo', 'danger');
        });
    }
    
    // Función para mostrar información del archivo
    function showFileInfo(file) {
        var fileName = file.name;
        var fileSize = formatFileSize(file.size);
        
        var fileNameElement = document.getElementById('transfer_file_name');
        var fileSizeElement = document.getElementById('transfer_file_size');
        var fileInfoElement = document.getElementById('transfer_file_info');
        var fileInput = document.getElementById('transfer_receipt_file');
        
        if (fileNameElement) fileNameElement.textContent = fileName;
        if (fileSizeElement) fileSizeElement.textContent = 'Tamaño: ' + fileSize;
        if (fileInfoElement) fileInfoElement.style.display = 'block';
        
        if (fileInput) {
            fileInput.classList.add('is-valid');
            fileInput.classList.remove('is-invalid');
        }
    }
    
    // Función para ocultar información del archivo
    function hideFileInfo() {
        var fileInfoElement = document.getElementById('transfer_file_info');
        var fileInput = document.getElementById('transfer_receipt_file');
        
        if (fileInfoElement) fileInfoElement.style.display = 'none';
        if (fileInput) {
            fileInput.classList.remove('is-valid', 'is-invalid');
        }
    }
    
    // Función para formatear tamaño de archivo
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        var k = 1024;
        var sizes = ['Bytes', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Función para validar tipo de archivo
    function validateFileType(file) {
        var allowedTypes = [
            'application/pdf',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ];
        return allowedTypes.includes(file.type) || 
               file.name.toLowerCase().match(/\.(pdf|jpg|jpeg|png|doc|docx|txt)$/);
    }
    
    // Función para validar tamaño de archivo
    function validateFileSize(file, maxSize) {
        return file.size <= maxSize;
    }
    
    // Función para mostrar mensaje
    function showMessage(message, type) {
        var alertClass = 'alert-' + type;
        var alertHtml = '<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert">' +
                       '<i class="fa fa-' + (type === 'success' ? 'check-circle' : 'exclamation-triangle') + ' me-2"></i>' +
                       message +
                       '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                       '</div>';
        
        // Remover alertas existentes
        var existingAlerts = document.querySelectorAll('.alert-dismissible');
        existingAlerts.forEach(function(alert) {
            alert.remove();
        });
        
        // Agregar nueva alerta
        var fileInput = document.getElementById('transfer_receipt_file');
        if (fileInput) {
            var cardBody = fileInput.closest('.card-body');
            if (cardBody) {
                var tempDiv = document.createElement('div');
                tempDiv.innerHTML = alertHtml;
                var newAlert = tempDiv.firstChild;
                cardBody.insertBefore(newAlert, cardBody.firstChild);
                
                // Auto-ocultar después de 5 segundos
                setTimeout(function() {
                    if (newAlert && newAlert.parentNode) {
                        newAlert.style.opacity = '0';
                        newAlert.style.transition = 'opacity 0.5s';
                        setTimeout(function() {
                            if (newAlert.parentNode) {
                                newAlert.remove();
                            }
                        }, 500);
                    }
                }, 5000);
            }
        }
    }
    
    // Inicializar cuando el DOM esté listo
    var fileInput = document.getElementById('transfer_receipt_file');
    
    if (fileInput) {
        ensureFormEnctype();
        
        // Vincular evento de cambio
        fileInput.addEventListener('change', function(ev) {
            var file = ev.target.files[0];
            if (file) {
                if (validateFileType(file)) {
                    if (validateFileSize(file, 10 * 1024 * 1024)) {
                        showFileInfo(file);
                        showMessage('Archivo seleccionado correctamente', 'success');
                        
                        // Enviar archivo al servidor
                        uploadFileToServer(file);
                    } else {
                        showMessage('El archivo es demasiado grande. Máximo 10MB permitido.', 'danger');
                        this.value = '';
                        hideFileInfo();
                    }
                } else {
                    showMessage('Tipo de archivo no permitido. Use PDF, JPG, PNG, DOC, DOCX o TXT.', 'danger');
                    this.value = '';
                    hideFileInfo();
                }
            } else {
                hideFileInfo();
            }
        });
    } else {
        // Intentar con un selector más amplio
        var allFileInputs = document.querySelectorAll('input[type="file"]');
    }
}); 