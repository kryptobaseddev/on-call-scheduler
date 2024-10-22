export function initializeTimeOff() {
    const timeOffForm = document.getElementById('time-off-form');
    if (timeOffForm) {
        timeOffForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            
            fetch('/time_off', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.msg === "Time-off request submitted") {
                    location.reload();
                } else {
                    alert('Failed to submit time-off request. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
}
