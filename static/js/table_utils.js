export function initializeTableSearch(searchInputId, tableBodyId) {
    const searchInput = document.getElementById(searchInputId);
    const tableBody = document.getElementById(tableBodyId);

    if (searchInput && tableBody) {
        searchInput.addEventListener('input', function(e) {
            const searchText = e.target.value.toLowerCase();
            const rows = tableBody.getElementsByTagName('tr');
            
            for (let row of rows) {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchText)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            }
        });
    }
}

export function initializeSelectAll(selectAllId, checkboxName, deleteButtonId) {
    const selectAll = document.getElementById(selectAllId);
    const deleteButton = document.getElementById(deleteButtonId);
    const checkboxes = document.getElementsByName(checkboxName);

    if (selectAll && deleteButton && checkboxes.length > 0) {
        selectAll.addEventListener('change', function() {
            checkboxes.forEach(checkbox => checkbox.checked = this.checked);
            updateDeleteButton();
        });

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateDeleteButton);
        });

        function updateDeleteButton() {
            const checkedBoxes = document.querySelectorAll(`input[name="${checkboxName}"]:checked`);
            deleteButton.disabled = checkedBoxes.length === 0;
        }
    }
}