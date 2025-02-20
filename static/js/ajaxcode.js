document.addEventListener("DOMContentLoaded", function () {
    // Event listener for dynamically created elements
    document.getElementById("work-entries").addEventListener("change", function (event) {
        if (event.target.matches('select[name="current_place_of_employment[]"]')) {
            let employmentSelect = event.target;
            let workEntry = employmentSelect.closest('.work-entry'); // Find parent container
            
            let endDateInput = workEntry.querySelector('input[name="end-date[]"]');

            if (employmentSelect.value === "Yes") {
                // Clear value and disable the end date field
                endDateInput.value = "";
                endDateInput.disabled = true;
            } else {
                // Enable the end date field for manual selection
                endDateInput.disabled = false;
            }
        }
    });
});
