document.addEventListener("alpine:init", () => {
  Alpine.data("CHIETASSDDPHASE1", () => {
    return {
      StudentRegister: true,
      CompanyRegister: false,
      filter_container: false,
      Admin_all_result: true,
      Admin_filter: false,


      openHome(currentSection) {
        // Reset sections to false by default
        this.StudentRegister = false;
        this.CompanyRegister = false;
        this.Admin_all_result = true;
        this.Admin_filter = false;

        // Set the active section based on the button clicked
        if (currentSection === "StudentRegister") {
          this.StudentRegister = true;
        } else if (currentSection === "CompanyRegister") {
          this.CompanyRegister = true;
        }else if (currentSection === "Admin_all_result") {
          this.CompanyRegister = true;
        }else if (currentSection === "Admin_filter") {
          this.Admin_filter = true;
          this.Admin_all_result= false;
        }
      },

      init() {
        // Any additional initialization logic if required
      },
    };
  });
});
