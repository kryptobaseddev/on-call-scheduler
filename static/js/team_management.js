export function initializeTeamManagement() {
    var el = document.getElementById('sortableList');
    if (el) {
        new Sortable(el, {
            animation: 150,
            ghostClass: 'blue-background-class',
            handle: '.handle',
            onEnd: updateCallSequenceNumbers
        });
    }
}

export function updateCallSequenceNumbers() {
    const listItems = document.querySelectorAll('#sortableList li');
    listItems.forEach((item, index) => {
        item.querySelector('.call-sequence-number').textContent = index + 1;
    });
}

// document.addEventListener('DOMContentLoaded', initializeTeamManagement);
