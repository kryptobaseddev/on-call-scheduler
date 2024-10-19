document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === "success") {
                    window.location.href = data.redirect;
                } else {
                    const errorMessage = document.getElementById('error-message');
                    if (errorMessage) {
                        errorMessage.textContent = data.message;
                        errorMessage.style.display = 'block';
                    } else {
                        alert(data.message);
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            });
        });
    }

    document.querySelectorAll('.delete-note').forEach(button => {
        button.addEventListener('click', function() {
            const noteId = this.dataset.noteId;
            const deleteUrl = `/manager/delete_note/${noteId}`;
            showDeleteConfirmationModal(deleteUrl, () => location.reload());
        });
    });

    document.querySelectorAll('.delete-schedule').forEach(button => {
        button.addEventListener('click', function() {
            const scheduleId = this.dataset.scheduleId;
            const deleteUrl = `/manager/delete_schedule/${scheduleId}`;
            showDeleteConfirmationModal(deleteUrl, () => location.reload());
        });
    });
});
