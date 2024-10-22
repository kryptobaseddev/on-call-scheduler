export function initializeUserManagement() {
    document.querySelectorAll('.delete-user').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const deleteUrl = `/manager/delete_user/${userId}`;
            window.showDeleteConfirmationModal(deleteUrl, () => location.reload());
        });
    });

    document.querySelectorAll('.edit-user').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const editUrl = `/manager/edit_user/${userId}`;
            window.showEditUserModal(editUrl);
        });
    });

    document.querySelectorAll('.toggle-user-status').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const toggleUrl = `/manager/toggle_user_status/${userId}`;
            window.toggleUserStatus(toggleUrl);
        });
    });
}
