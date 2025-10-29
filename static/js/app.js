// Loan Management System JavaScript

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('fade-in');
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        }
    });

    return isValid;
}

// AJAX functions
async function makeAjaxRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.message || 'Request failed');
        }

        return result;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// Loan management functions
function approveLoan(loanId) {
    if (confirm('Are you sure you want to approve this loan?')) {
        makeAjaxRequest(`/api/loan/${loanId}/approve`, 'POST')
            .then(result => {
                if (result.success) {
                    location.reload();
                }
            })
            .catch(error => {
                alert('Error approving loan: ' + error.message);
            });
    }
}

function rejectLoan(loanId) {
    if (confirm('Are you sure you want to reject this loan?')) {
        makeAjaxRequest(`/api/loan/${loanId}/reject`, 'POST')
            .then(result => {
                if (result.success) {
                    location.reload();
                }
            })
            .catch(error => {
                alert('Error rejecting loan: ' + error.message);
            });
    }
}

// Payment calculation
function calculatePayment() {
    const principal = parseFloat(document.getElementById('principal_amount')?.value || 0);
    const rate = parseFloat(document.getElementById('interest_rate')?.value || 0);
    const term = parseInt(document.getElementById('loan_term')?.value || 0);

    if (principal > 0 && rate > 0 && term > 0) {
        const monthlyRate = rate / 100 / 12;
        const monthlyPayment = principal * (monthlyRate * Math.pow(1 + monthlyRate, term)) / 
                              (Math.pow(1 + monthlyRate, term) - 1);
        
        document.getElementById('monthly_payment_display').textContent = 
            '₹' + monthlyPayment.toFixed(2);
        document.getElementById('total_payment_display').textContent = 
            '₹' + (monthlyPayment * term).toFixed(2);
    }
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Show loading spinner
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div>';
    }
}

// Hide loading spinner
function hideLoading(elementId, content) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = content;
    }
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Search functionality
function searchLoans(query) {
    const rows = document.querySelectorAll('#loansTable tbody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query.toLowerCase()) ? '' : 'none';
    });
}

// Export to CSV
function exportToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tr'));
    const csvContent = rows.map(row => {
        return Array.from(row.querySelectorAll('td, th'))
            .map(cell => `"${cell.textContent.trim()}"`)
            .join(',');
    }).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Print functionality
function printTable(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
            <head>
                <title>Print Report</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-4">
                    ${table.outerHTML}
                </div>
            </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
}

// Chart initialization (placeholder for future chart.js integration)
function initializeCharts() {
    // This function can be extended to initialize various charts
    console.log('Charts initialized');
}

// Real-time notifications (placeholder for future WebSocket integration)
function initializeNotifications() {
    // This function can be extended to show real-time notifications
    console.log('Notifications initialized');
}

// Dark mode toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

// Load dark mode preference
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
    }
});

// Error handling
function handleError(error, elementId = 'error-message') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = error.message || 'An error occurred';
        element.style.display = 'block';
    }
}

// Success message
function showSuccess(message, elementId = 'success-message') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.style.display = 'block';
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

// Initialize all functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    initializeNotifications();
});
