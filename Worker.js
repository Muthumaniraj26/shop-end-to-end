document.addEventListener('DOMContentLoaded', function() {
    // Confirmation for adding/updating a product
    const addProductForm = document.getElementById('add-product-form');
    if(addProductForm) {
        addProductForm.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to submit this product? This will create a new product or add stock to an existing one.')) {
                e.preventDefault();
            }
        });
    }

    // Confirmation for refilling stock
    document.querySelectorAll('.refill-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const qtyInput = this.querySelector('input[name="qty"]');
            const productName = this.closest('tr').querySelector('td:nth-child(2)').textContent.trim();
            if (!confirm(`Are you sure you want to add ${qtyInput.value} units to "${productName}"?`)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-dismiss flash messages
    document.querySelectorAll('.flash-message').forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s ease';
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 500);
        }, 5000);
    });
});
