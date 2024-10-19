function showNotification(type, message) {
    const notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    document.getElementById('notification-container').appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function showDeleteConfirmationModal(deleteUrl, onSuccess) {
    const confirmDeleteButton = document.getElementById('confirmDeleteButton');
    const deleteConfirmationModal = new bootstrap.Modal(document.getElementById('deleteConfirmationModal'));

    confirmDeleteButton.onclick = function() {
        fetch(deleteUrl, {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                if (onSuccess) onSuccess();
                showNotification('success', 'Item deleted successfully.');
            } else {
                showNotification('danger', data.message || 'Error deleting item.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('danger', 'An unexpected error occurred. Please try again.');
        })
        .finally(() => {
            deleteConfirmationModal.hide();
        });
    };

    deleteConfirmationModal.show();
}
