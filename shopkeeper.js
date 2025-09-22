document.addEventListener('DOMContentLoaded', function() {
    // Live search filter for products
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            let filter = this.value.toLowerCase();
            document.querySelectorAll('.products-table tbody tr').forEach(row => {
                const nameCell = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
                row.style.display = nameCell.includes(filter) ? '' : 'none';
            });
        });
    }

    // Add confirmation to 'Add to Cart' forms
    document.querySelectorAll('.sell-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const qtyInput = this.querySelector('input[name="qty"]');
            const productName = this.closest('tr').querySelector('td:nth-child(2)').textContent.trim();
            if (!confirm(`Add ${qtyInput.value} unit(s) of "${productName}" to the cart?`)) {
                e.preventDefault();
            }
        });
    });

    // Function to generate and download a text bill
    function generateAndDownloadBill() {
        const customerName = document.getElementById('customer_name').value.trim() || 'Valued Customer';
        const cartRows = document.querySelectorAll('.cart-table tbody tr');
        const total = document.querySelector('.cart-total').textContent.trim();
        const now = new Date();
        
        let billContent = `==============================\n`;
        billContent += `      INVOICE RECEIPT\n`;
        billContent += `==============================\n\n`;
        billContent += `Sold To: ${customerName}\n`;
        billContent += `Date: ${now.toLocaleDateString()}\n`;
        billContent += `Time: ${now.toLocaleTimeString()}\n\n`;
        billContent += `------------------------------\n`;
        billContent += `Items Purchased\n`;
        billContent += `------------------------------\n`;
        
        cartRows.forEach(row => {
            const name = row.cells[0].textContent.trim();
            const qty = row.cells[1].textContent.trim();
            const subtotal = row.cells[2].textContent.trim();
            billContent += `${name} (x${qty}) - ${subtotal}\n`;
        });
        
        billContent += `------------------------------\n`;
        billContent += `${total}\n`;
        billContent += `==============================\n\n`;
        billContent += `Thank you for your purchase!\n`;

        const blob = new Blob([billContent], { type: 'text/plain' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `receipt-${now.getTime()}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Handle the payment form submission
    const payForm = document.getElementById('pay-form');
    if (payForm) {
        payForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (confirm('Are you sure you want to complete this purchase? This will update stock levels.')) {
                // Show spinner on pay button
                const payButton = document.getElementById('confirm-pay-btn');
                const spinner = payButton.querySelector('.spinner-border');
                payButton.disabled = true;
                spinner.classList.remove('d-none');
                
                generateAndDownloadBill();
                
                // Allow the form to submit after a short delay to ensure download starts
                setTimeout(() => {
                    this.submit();
                }, 500);
            }
        });
    }
    
    // Add confirmation to 'Clear Cart' form
    const clearCartForm = document.getElementById('clear-cart-form');
    if (clearCartForm) {
        clearCartForm.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to clear the entire cart?')) {
                e.preventDefault();
            }
        });
    }

    // Client-side validation for quantity inputs
    document.querySelectorAll('.qty-input').forEach(input => {
        input.addEventListener('change', function() {
            const min = parseInt(this.min, 10);
            const max = parseInt(this.max, 10);
            let value = parseInt(this.value, 10);

            if (isNaN(value) || value < min) {
                this.value = min;
            } else if (value > max) {
                this.value = max;
                alert(`Maximum stock available for this item is ${max}.`);
            }
        });
    });

    // Auto-dismiss flash messages after 5 seconds
    document.querySelectorAll('.flash-message').forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 500); // Wait for fade out transition
        }, 5000);
    });
});
