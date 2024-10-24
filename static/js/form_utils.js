export function initializeFlatpickr() {
    const flatpickrElements = document.querySelectorAll(".flatpickr-datetime");
    if (flatpickrElements.length > 0) {
        flatpickr(".flatpickr-datetime", {
            enableTime: true,
            dateFormat: "Y-m-d H:i",
            time_24hr: true,
            defaultHour: 0,
            defaultMinute: 0
        });
    }
}