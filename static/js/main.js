// Smart Campus Analytics - Core Application JS
document.addEventListener('DOMContentLoaded', function() {
    console.log("Smart Campus Analytics Platform Initialized.");

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
