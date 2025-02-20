// Wait for the DOM to load before running the script
document.addEventListener("DOMContentLoaded", function (event) {

    /**
     * Function: showNavbar
     * Purpose: Toggle the visibility of the sidebar navigation when the toggle button is clicked.
     * Also toggles padding on the body and header for a consistent layout.
     */
    const showNavbar = (toggleId, navId, bodyId, headerId) => {
        const toggle = document.getElementById(toggleId),
              nav = document.getElementById(navId),
              bodypd = document.getElementById(bodyId),
              headerpd = document.getElementById(headerId);

        // Ensure all elements exist
        if (toggle && nav && bodypd && headerpd) {
            toggle.addEventListener('click', () => {
                // Toggle the 'show' class to display or hide the navbar
                nav.classList.toggle('show');
                // Toggle the icon class for a visual change (e.g., menu to close icon)
                toggle.classList.toggle('bx-x');
                // Toggle padding on the body and header for layout adjustment
                bodypd.classList.toggle('body-pd');
                headerpd.classList.toggle('body-pd');
            });
        }
    };

    // Initialize the navbar toggle functionality
    showNavbar('header-toggle', 'nav-bar', 'body-pd', 'header');

    /* Make clicked navigation links black*/
    const linkColor = document.querySelectorAll('.nav_link');

    /**
     * Function: colorLink
     * Purpose: Remove the 'active' class from all nav links and add it to the clicked one.
     */
    function colorLink() {
        if (linkColor) {
            linkColor.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        }
    }
    // Attach click event to each navigation link
    linkColor.forEach(l => l.addEventListener('click', colorLink));

});