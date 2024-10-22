export function initializeColorManager() {
    const colorOptions = document.querySelectorAll('.color-option');
    const colorInput = document.getElementById('color') || document.getElementById('color_id');
    const currentColorSpan = document.getElementById('currentColor');
    const usedColorsElement = document.getElementById('usedColors');
    let selectedColorId = null;

    if (usedColorsElement) {
        const usedColors = new Set(JSON.parse(usedColorsElement.textContent));

        colorOptions.forEach(option => {
            const colorId = option.dataset.colorId;
            if (usedColors.has(parseInt(colorId))) {
                option.classList.add('unavailable');
                option.style.cursor = 'not-allowed';
                option.style.opacity = '0.5';
                option.title = "This color is already assigned to another team.";
            } else {
                option.addEventListener('click', function() {
                    if (!this.classList.contains('unavailable')) {
                        colorOptions.forEach(opt => opt.classList.remove('selected'));
                        this.classList.add('selected');
                        selectedColorId = colorId;
                    }
                });
            }
        });

        const confirmButton = document.getElementById('confirmColorSelection');
        if (confirmButton) {
            confirmButton.addEventListener('click', function() {
                if (selectedColorId) {
                    if (colorInput) {
                        colorInput.value = selectedColorId;
                    }
                    if (currentColorSpan) {
                        currentColorSpan.style.backgroundColor = colorOptions[selectedColorId - 1].style.backgroundColor;
                    }
                    const modalElement = document.getElementById('colorModal');
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) {
                        modal.hide();
                    }
                }
            });
        }
    }
}
