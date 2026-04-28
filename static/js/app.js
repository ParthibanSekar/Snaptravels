
// SnapTravels JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search forms
    initSearchForms();
    
    // Initialize booking forms
    initBookingForms();
    
    // Initialize navigation
    initNavigation();
});

function initSearchForms() {
    // Flight search form enhancements
    const flightForm = document.getElementById('flightSearchForm');
    if (flightForm) {
        // Set minimum date to today
        const departDate = flightForm.querySelector('input[name="depart_date"]');
        if (departDate) {
            departDate.min = new Date().toISOString().split('T')[0];
        }
        
        const returnDate = flightForm.querySelector('input[name="return_date"]');
        if (returnDate) {
            returnDate.min = new Date().toISOString().split('T')[0];
        }
        
        // Update return date minimum when departure date changes
        if (departDate && returnDate) {
            departDate.addEventListener('change', function() {
                returnDate.min = this.value;
                if (returnDate.value && returnDate.value < this.value) {
                    returnDate.value = this.value;
                }
            });
        }
    }
    
    // Hotel search form enhancements
    const hotelForm = document.getElementById('hotelSearchForm');
    if (hotelForm) {
        const checkinDate = hotelForm.querySelector('input[name="checkin"]');
        const checkoutDate = hotelForm.querySelector('input[name="checkout"]');
        
        if (checkinDate) {
            checkinDate.min = new Date().toISOString().split('T')[0];
        }
        
        if (checkoutDate) {
            checkoutDate.min = new Date().toISOString().split('T')[0];
        }
        
        // Update checkout date minimum when checkin date changes
        if (checkinDate && checkoutDate) {
            checkinDate.addEventListener('change', function() {
                const nextDay = new Date(this.value);
                nextDay.setDate(nextDay.getDate() + 1);
                checkoutDate.min = nextDay.toISOString().split('T')[0];
                
                if (checkoutDate.value && checkoutDate.value <= this.value) {
                    checkoutDate.value = nextDay.toISOString().split('T')[0];
                }
            });
        }
    }
}

function initBookingForms() {
    // Credit card number formatting
    const cardNumberInput = document.querySelector('input[name="card_number"]');
    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', function() {
            let value = this.value.replace(/\s/g, '').replace(/[^0-9]/gi, '');
            let matches = value.match(/\d{4,16}/g);
            let match = matches && matches[0] || '';
            let parts = [];
            
            for (let i = 0; i < match.length; i += 4) {
                parts.push(match.substring(i, i + 4));
            }
            
            if (parts.length) {
                this.value = parts.join(' ');
            } else {
                this.value = value;
            }
        });
        
        cardNumberInput.addEventListener('keypress', function(e) {
            if (e.which !== 8 && e.which !== 0 && (e.which < 48 || e.which > 57) && e.which !== 32) {
                e.preventDefault();
            }
        });
    }
    
    // CVV input validation
    const cvvInput = document.querySelector('input[name="cvv"]');
    if (cvvInput) {
        cvvInput.addEventListener('keypress', function(e) {
            if (e.which !== 8 && e.which !== 0 && (e.which < 48 || e.which > 57)) {
                e.preventDefault();
            }
        });
    }
    
    // Phone number formatting
    const phoneInput = document.querySelector('input[name="customer_phone"]');
    if (phoneInput) {
        phoneInput.addEventListener('keypress', function(e) {
            if (e.which !== 8 && e.which !== 0 && (e.which < 48 || e.which > 57) && 
                e.which !== 43 && e.which !== 45 && e.which !== 32) {
                e.preventDefault();
            }
        });
    }
}

function initNavigation() {
    // Active navigation highlighting
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar a');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.fontWeight = 'bold';
            link.style.textDecoration = 'underline';
        }
    });
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    return new Date(dateString).toLocaleDateString('en-IN', options);
}
