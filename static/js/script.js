// Global JavaScript for QBO Invoice Converter

// Enable popovers and tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add validation classes to forms
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Format currency values
function formatCurrency(value) {
    if (!value) return '';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(value);
}

// Format date values
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(date);
}

// Toggle all checkboxes
function toggleAllCheckboxes(sourceCheckbox, targetName) {
    const checkboxes = document.querySelectorAll(`input[name^="${targetName}"]`);
    checkboxes.forEach(checkbox => {
        checkbox.checked = sourceCheckbox.checked;
    });
}

// Confirm before navigating away with unsaved changes
function confirmNavigation(event) {
    // Check if there are any unsaved changes
    if (window.hasUnsavedChanges) {
        const confirmationMessage = 'You have unsaved changes. Are you sure you want to leave this page?';
        (event || window.event).returnValue = confirmationMessage;
        return confirmationMessage;
    }
}

// Utility function to download a file from a blob
function downloadFile(content, fileName, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
} 