document.addEventListener('DOMContentLoaded', function() {
    // Live search for users table
    const userSearch = document.getElementById('userSearchInput');
    if (userSearch) {
        userSearch.addEventListener('keyup', function() {
            let filter = this.value.toLowerCase();
            document.querySelectorAll('#usersTable tbody tr').forEach(row => {
                const nameCell = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
                const roleCell = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
                row.style.display = (nameCell.includes(filter) || roleCell.includes(filter)) ? '' : 'none';
            });
        });
    }

    // Live search for products table
    const productSearch = document.getElementById('productSearchInput');
    if (productSearch) {
        productSearch.addEventListener('keyup', function() {
            let filter = this.value.toLowerCase();
            document.querySelectorAll('#productsTable tbody tr').forEach(row => {
                const nameCell = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
                row.style.display = nameCell.includes(filter) ? '' : 'none';
            });
        });
    }

    // Confirmation for deleting users
    document.querySelectorAll('.delete-user-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Confirmation for deleting products
    document.querySelectorAll('.delete-product-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this product? This will remove it permanently.')) {
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
s
