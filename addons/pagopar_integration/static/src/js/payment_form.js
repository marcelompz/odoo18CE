/** @odoo-module **/

// Simplified Pagopar JavaScript without complex dependencies
// Core payment flow now handled by redirect template

document.addEventListener('DOMContentLoaded', function() {

    // Status checker functionality
    const statusButtons = document.querySelectorAll('.btn-check-status');
    statusButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const orderId = this.dataset.orderId;

            if (!orderId) {
                showMessage('error', 'ID de orden no encontrado');
                return;
            }

            setButtonLoading(this, true);

            // Simple AJAX call without imports
            fetch('/payment/pagopar/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {order_id: orderId}
                })
            })
            .then(response => response.json())
            .then(result => {
                if (result.result && result.result.success) {
                    if (result.result.status === 'done') {
                        showMessage('success', '¡Pago confirmado! Recargando página...');
                        setTimeout(() => location.reload(), 10000);
                    } else if (result.result.status === 'pending') {
                        showMessage('warning', 'El pago aún está pendiente');
                    } else {
                        showMessage('info', 'Estado del pago: ' + result.result.status);
                    }
                } else {
                    showMessage('error', 'Error al verificar estado: ' + (result.result ? result.result.error : 'Error desconocido'));
                }
            })
            .catch(error => {
                showMessage('error', 'Error de conexión al verificar el estado');
            })
            .finally(() => {
                setButtonLoading(this, false);
            });
        });
    });

    // Payment method selection
    const paymentWidgets = document.querySelectorAll('.pagopar-payment-widget');
    paymentWidgets.forEach(widget => {
        widget.addEventListener('click', function(e) {
            e.preventDefault();

            // Remove selection from all widgets
            paymentWidgets.forEach(w => w.classList.remove('selected'));

            // Add selection to clicked widget
            this.classList.add('selected');

            // Update form inputs
            const providerInput = document.querySelector('input[name="payment_provider"]');
            const codeInput = document.querySelector('input[name="provider_code"]');

            if (providerInput) providerInput.value = 'pagopar';
            if (codeInput) codeInput.value = 'pagopar';

            // Dispatch custom event
            this.dispatchEvent(new CustomEvent('pagopar:payment_method_selected', {
                detail: { provider: 'pagopar' }
            }));
        });
    });

    // Filter functionality for payments portal
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const filterValue = this.dataset.filter;

            // Update active button
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // Apply filter
            applyFilter(filterValue);
        });
    });

    // Sort functionality
    const sortButtons = document.querySelectorAll('.sort-btn');
    sortButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const sortValue = this.dataset.sort;

            // Update active button
            sortButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // Apply sort
            applySort(sortValue);
        });
    });
});

// Helper functions
function setButtonLoading(button, loading) {
    button.disabled = loading;
    const icon = button.querySelector('.fa');
    if (icon) {
        if (loading) {
            icon.classList.remove('fa-refresh');
            icon.classList.add('fa-spinner', 'fa-spin');
        } else {
            icon.classList.remove('fa-spinner', 'fa-spin');
            icon.classList.add('fa-refresh');
        }
    }
}

function showMessage(type, message) {
    let alertClass = 'alert-info';
    if (type === 'success') alertClass = 'alert-success';
    else if (type === 'error') alertClass = 'alert-danger';
    else if (type === 'warning') alertClass = 'alert-warning';

    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-dismissible`;
    alert.innerHTML = `
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        ${message}
    `;

    // Find container and show alert
    const container = document.querySelector('.pagopar-status-checker') || document.body;
    const existingAlerts = container.querySelectorAll('.alert');
    existingAlerts.forEach(oldAlert => oldAlert.remove());

    container.prepend(alert);
    setTimeout(() => alert.remove(), 5000);
}

function applyFilter(filter) {
    const rows = document.querySelectorAll('tbody tr');

    rows.forEach(row => {
        if (filter === 'all') {
            row.style.display = '';
        } else {
            const badge = row.querySelector('.badge');
            const status = badge ? badge.textContent.toLowerCase() : '';

            if (status.includes(filter)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });

    updateNoResultsMessage();
}

function applySort(sort) {
    const tbody = document.querySelector('tbody');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));

    rows.sort((a, b) => {
        let aValue, bValue;

        switch(sort) {
            case 'date':
                aValue = new Date(a.querySelector('td:nth-child(2)').textContent);
                bValue = new Date(b.querySelector('td:nth-child(2)').textContent);
                return bValue - aValue;
            case 'amount':
                aValue = parseFloat(a.querySelector('td:nth-child(3)').textContent.replace(/[^\d.]/g, ''));
                bValue = parseFloat(b.querySelector('td:nth-child(3)').textContent.replace(/[^\d.]/g, ''));
                return bValue - aValue;
            case 'reference':
                aValue = a.querySelector('td:first-child').textContent.toLowerCase();
                bValue = b.querySelector('td:first-child').textContent.toLowerCase();
                return aValue.localeCompare(bValue);
            default:
                return 0;
        }
    });

    rows.forEach(row => tbody.appendChild(row));
}

function updateNoResultsMessage() {
    const tbody = document.querySelector('tbody');
    if (!tbody) return;

    const visibleRows = tbody.querySelectorAll('tr:not([style*="display: none"])');
    let noResultsRow = tbody.querySelector('.no-results-row');

    if (visibleRows.length === 0) {
        if (!noResultsRow) {
            noResultsRow = document.createElement('tr');
            noResultsRow.className = 'no-results-row';
            noResultsRow.innerHTML = `
                <td colspan="6" class="text-center text-muted">
                    <i class="fa fa-search fa-2x mb-2"></i><br/>
                    No se encontraron pagos con los filtros seleccionados
                </td>
            `;
            tbody.appendChild(noResultsRow);
        }
    } else if (noResultsRow) {
        noResultsRow.remove();
    }
}
