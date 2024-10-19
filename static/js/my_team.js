document.addEventListener('DOMContentLoaded', function() {
    // Existing code...

    document.querySelectorAll('.archive-note').forEach(button => {
        button.addEventListener('click', function() {
            const noteId = this.dataset.noteId;
            fetch(`/manager/archive_note/${noteId}`, {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    showNotification('danger', 'Error archiving note');
                }
            });
        });
    });

    document.querySelectorAll('.activate-note').forEach(button => {
        button.addEventListener('click', function() {
            const noteId = this.dataset.noteId;
            fetch(`/manager/unarchive_note/${noteId}`, {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    showNotification('danger', 'Error activating note');
                }
            });
        });
    });
});
