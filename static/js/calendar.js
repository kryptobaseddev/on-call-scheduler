export function initializeCalendar() {
    var calendarEl = document.getElementById('calendar');
    if (calendarEl) {
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            events: calendarEvents,  // We'll need to ensure this variable is available
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek'
            },
            eventDidMount: function(info) {
                new bootstrap.Tooltip(info.el, {
                    title: `Team: ${info.event.extendedProps.teamName}<br>
                            User: ${info.event.extendedProps.userName}<br>
                            Phone: ${info.event.extendedProps.mobilePhone}`,
                    html: true,
                    placement: 'top',
                    trigger: 'hover',
                    container: 'body'
                });
            }
        });
        calendar.render();

        // Toggle between monthly and weekly views
        var viewToggle = document.getElementById('viewToggle');
        if (viewToggle) {
            viewToggle.addEventListener('change', function(e) {
                calendar.changeView(e.target.checked ? 'timeGridWeek' : 'dayGridMonth');
            });
        }
    }
}
