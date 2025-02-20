
// Section for add work history 


document.addEventListener("DOMContentLoaded", function () {
    const workHistoryForm = document.getElementById("work-history-form");
    const addWorkButton = document.getElementById("add-work");
    const removeWorkButton = document.getElementById("remove-work");
    const workEntriesContainer = document.getElementById("work-entries");

    function updateRemoveButton() {
        removeWorkButton.disabled = workEntriesContainer.children.length <= 1;
    }

    function updateEndDateBehavior(workEntry) {
        let employmentSelect = workEntry.querySelector('select[name="current_place_of_employment[]"]');
        let endDateInput = workEntry.querySelector('input[name="end-date[]"]');

        employmentSelect.addEventListener("change", function () {
            if (employmentSelect.value === "Yes") {
                endDateInput.value = "";
                endDateInput.disabled = true;
            } else {
                endDateInput.disabled = false;
            }
        });
    }

    // Apply behavior to existing work entries
    document.querySelectorAll('.work-entry').forEach(updateEndDateBehavior);

    addWorkButton.addEventListener("click", function (e) {
        e.preventDefault();

        // ✅ Create a new work entry
        const newEntry = document.createElement("div");
        newEntry.classList.add("work-entry", "border", "p-3", "mb-3");

        newEntry.innerHTML = `
            <hr>
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label"><b>Employer</b></label>
                    <input type="text" class="form-control" name="employer_names[]" placeholder="Enter Employer name" required>
                </div>
                <div class="col-md-6">
                    <label class="form-label"><b>Job Title</b></label>
                    <input type="text" class="form-control" name="job-title[]" placeholder="Enter Job Title" required>
                </div>
            </div>

            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label"><b>Current place of employment?</b></label>
                    <select class="form-select" name="current_place_of_employment[]">
                        <option value="">-- Currently Employed --</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label"><b>Start Date</b></label>
                    <input type="date" class="form-control" name="start-date[]" required>
                </div>
                <div class="col-md-4">
                    <label class="form-label"><b>End Date</b></label>
                    <input type="date" class="form-control" name="end-date[]">
                </div>
            </div>

            <div class="mb-3">
                <label for="tell_about_yourself" class="form-label"><b>Job Description</b></label>
                <textarea class="form-control" name="job-description[]" rows="4" placeholder="Provide a job description"></textarea>
            </div>
        `;

        // Append the new entry to the container
        workEntriesContainer.appendChild(newEntry);

        // Apply end date behavior to new entry
        updateEndDateBehavior(newEntry);

        updateRemoveButton(); // Ensure the remove button is updated
    });

    removeWorkButton.addEventListener("click", function (e) {
        e.preventDefault();
        if (workEntriesContainer.children.length > 1) {
            workEntriesContainer.removeChild(workEntriesContainer.lastElementChild);
        }
        updateRemoveButton();
    });

    updateRemoveButton();
});




// TO control the end date 
document.addEventListener("DOMContentLoaded", function () {
    const workEntriesContainer = document.getElementById("work-entries");

    function updateEndDateBehavior(workEntry) {
        let employmentSelect = workEntry.querySelector('select[name="current_place_of_employment[]"]');
        let endDateInput = workEntry.querySelector('input[name="end-date[]"]');

        employmentSelect.addEventListener("change", function () {
            if (employmentSelect.value === "Yes") {
                endDateInput.value = "";
                endDateInput.disabled = true;
                endDateInput.setAttribute("name", "end-date-disabled[]"); // Prevents browser from ignoring it
            } else {
                endDateInput.disabled = false;
                endDateInput.setAttribute("name", "end-date[]"); // Ensures form submission
            }
        });
    }

    // Apply behavior to all existing work entries
    document.querySelectorAll('.work-entry').forEach(updateEndDateBehavior);

    document.getElementById("work-history-form").addEventListener("submit", function () {
        document.querySelectorAll('.work-entry').forEach(workEntry => {
            let employmentSelect = workEntry.querySelector('select[name="current_place_of_employment[]"]');
            let endDateInput = workEntry.querySelector('input[name="end-date[]"]');

            // If "No" is selected but no end date is entered, prevent form submission
            if (employmentSelect.value === "No" && !endDateInput.value) {
                alert("Please enter an End Date for all 'No' entries before submitting.");
                event.preventDefault();
            }
        });
    });
});




// Section for education 



// cv 
document.addEventListener("DOMContentLoaded", function () {
    const cvForm = document.getElementById("cv-form");
    const addCVButton = document.getElementById("add-cv");
    const removeCVButton = document.getElementById("remove-cv");
    const cvEntriesContainer = document.getElementById("cv-entries");

    function updateRemoveButton() {
        if (cvEntriesContainer.children.length > 1) {
            removeCVButton.disabled = false; // Enable remove button
        } else {
            removeCVButton.disabled = true; // Disable remove button
        }
    }

    addCVButton.addEventListener("click", function (e) {
        e.preventDefault();

        const uniqueId = Date.now(); // Unique ID for each new entry

        const newCVEntry = document.createElement("div");
        newCVEntry.classList.add("cv-entry", "border", "p-3", "mb-3");
        newCVEntry.setAttribute("id", `cv-entry-${uniqueId}`);

        newCVEntry.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label"><b>Document Type (*)</b></label>
                    <select class="form-select" name="document-type[]" required>
                        <option value="">-- Select Document Type --</option>
                        <option value="Resume">Resume</option>
                        <option value="Cover Letter">Cover Letter</option>
                        <option value="Certificates">Certificates</option>
                        <option value="Other">Other</option>
                    </select>
                </div>

                <div class="col-md-6">
                    <label class="form-label"><b>Upload Document (*)</b></label>
                    <input type="file" class="form-control" name="cv-file[]" required>
                </div>
            </div>
        `;

        cvEntriesContainer.appendChild(newCVEntry);
        updateRemoveButton(); // Update remove button state
    });

    removeCVButton.addEventListener("click", function (e) {
        e.preventDefault();
        if (cvEntriesContainer.children.length > 1) {
            cvEntriesContainer.removeChild(cvEntriesContainer.lastElementChild);
        }
        updateRemoveButton(); // Update remove button state
    });

    updateRemoveButton(); // Ensure remove button state is set correctly on load
});


// Skills  
document.addEventListener("DOMContentLoaded", function () {
    const skillsForm = document.getElementById("skills-form");
    const addSkillsButton = document.getElementById("add-skill");
    const removeSkillsButton = document.getElementById("remove-skill");
    const skillsEntriesContainer = document.getElementById("skills-entries");

    function updateRemoveButton() {
        if (skillsEntriesContainer.children.length > 1) {
            removeSkillsButton.disabled = false; // Enable remove button
        } else {
            removeSkillsButton.disabled = true; // Disable remove button
        }
    }

    addSkillsButton.addEventListener("click", function (e) {
        e.preventDefault();

        const uniqueId = Date.now(); // Unique ID for each new entry

        const newSkillEntry = document.createElement("div");
        newSkillEntry.classList.add("skill-entry", "border", "p-3", "mb-3");
        newSkillEntry.setAttribute("id", `skill-entry-${uniqueId}`);

        newSkillEntry.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label"><b>Skills</b></label>
                    <select class="form-select" name="skills[]" required>
                        <option value="">-- Select a skill --</option>
                        <option value="Backend Development">Backend Development</option>
                        <option value="Frontend Development">Frontend Development</option>
                        <option value="Version Control">Version Control</option>
                        <option value="UI/UX Design">UI/UX Design</option>
                    </select>
                </div>

                <div class="col-md-6">
                    <label class="form-label"><b>Proficiency</b></label>
                    <select class="form-select" name="proficiency[]" required>
                        <option value="">-- Select Proficiency --</option>
                        <option value="Beginner">Beginner</option>
                        <option value="Intermediate">Intermediate</option>
                        <option value="Advanced">Advanced</option>
                    </select>
                </div>
            </div>
        `;

        skillsEntriesContainer.appendChild(newSkillEntry);
        updateRemoveButton(); // Update remove button state
    });

    removeSkillsButton.addEventListener("click", function (e) {
        e.preventDefault();
        if (skillsEntriesContainer.children.length > 1) {
            skillsEntriesContainer.removeChild(skillsEntriesContainer.lastElementChild);
        }
        updateRemoveButton(); // Update remove button state
    });

    updateRemoveButton(); // Ensure remove button state is set correctly on load
});


// Attachment 
document.addEventListener("DOMContentLoaded", function () {
    const addCvButton = document.getElementById("add-cv");
    const removeCvButton = document.getElementById("remove-cv");
    const cvEntriesContainer = document.getElementById("cv-entries");

    function updateRemoveButton() {
        removeCvButton.disabled = cvEntriesContainer.children.length <= 1;
    }

    addCvButton.addEventListener("click", function (e) {
        e.preventDefault();

        const newEntry = document.createElement("div");
        newEntry.classList.add("cv-entry", "border", "p-3", "mb-3");

        newEntry.innerHTML = `
            <hr>
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label"><b>Document Type (*)</b></label>
                    <select class="form-select" name="document-type[]" required>
                        <option value="">-- Select Document Type --</option>
                        <option value="Resume">Resume</option>
                        <option value="Cover Letter">Cover Letter</option>
                        <option value="Certificates">Certificates</option>
                        <option value="Other">Other</option>
                    </select>
                </div>

                <div class="col-md-6">
                    <label class="form-label"><b>Upload Document (*)</b></label>
                    <input type="file" class="form-control" name="document-upload[]" required>
                </div>
            </div>
        `;

        cvEntriesContainer.appendChild(newEntry);
        updateRemoveButton();
    });

    removeCvButton.addEventListener("click", function (e) {
        e.preventDefault();
        if (cvEntriesContainer.children.length > 1) {
            cvEntriesContainer.removeChild(cvEntriesContainer.lastElementChild);
        }
        updateRemoveButton();
    });

    updateRemoveButton();
});

