export function initializeNotes() {
    document.querySelectorAll('.archive-note, .unarchive-note').forEach(button => {
        button.addEventListener('click', function() {
            const noteId = this.dataset.noteId;
            const action = this.classList.contains('archive-note') ? 'archive' : 'unarchive';
            handleNoteAction(noteId, action);
        });
    });

    document.querySelectorAll('.delete-note').forEach(button => {
        button.addEventListener('click', function() {
            const noteId = this.dataset.noteId;
            const deleteUrl = `/manager/delete_note/${noteId}`;
            showDeleteConfirmationModal(deleteUrl, () => location.reload());
        });
    });
}

function handleNoteAction(noteId, action) {
    fetch(`/manager/${action}_note/${noteId}`, {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            showNotification('danger', `Error ${action}ing note`);
        }
    });
}

// document.addEventListener('DOMContentLoaded', initializeNotes);
