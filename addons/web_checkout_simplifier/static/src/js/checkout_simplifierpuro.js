document.addEventListener('DOMContentLoaded', function() {
    var radios = document.querySelectorAll('input[name="payment_method"]');
    var bankSection = document.getElementById('bank_transfer_section');
    radios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            if (this.dataset.code === 'transfer') {
                bankSection.style.display = '';
            } else {
                bankSection.style.display = 'none';
            }
        });
    });
});