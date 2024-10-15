document.addEventListener('DOMContentLoaded', function() {
    const scheduleForm = document.getElementById('schedule-form');
    if (scheduleForm) {
        scheduleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const userId = document.getElementById('user-select').value;
            const startTime = document.getElementById('start-time').value;
            const endTime = document.getElementById('end-time').value;
            
            fetch('/schedule', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `user_id=${encodeURIComponent(userId)}&start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.msg === "Schedule created") {
                    location.reload();
                } else {
                    alert('Failed to create schedule. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
});
