// Dashboard modals: Add Expense / Add Income
// Vanilla JS only — no frameworks, per project constraints.

document.addEventListener("DOMContentLoaded", function () {
    var openTriggers = document.querySelectorAll("[data-open-modal]");
    var closeTriggers = document.querySelectorAll("[data-close-modal]");

    function openModal(id) {
        var modal = document.getElementById(id);
        if (!modal) return;
        modal.hidden = false;
        document.body.classList.add("modal-open");
        var firstField = modal.querySelector("input, select");
        if (firstField) firstField.focus();
    }

    function closeModal(id) {
        var modal = document.getElementById(id);
        if (!modal) return;
        modal.hidden = true;
        document.body.classList.remove("modal-open");
    }

    openTriggers.forEach(function (btn) {
        btn.addEventListener("click", function () {
            openModal(btn.getAttribute("data-open-modal"));
        });
    });

    closeTriggers.forEach(function (btn) {
        btn.addEventListener("click", function () {
            closeModal(btn.getAttribute("data-close-modal"));
        });
    });

    // Click on the dark overlay (outside the card) closes the modal.
    document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) {
                overlay.hidden = true;
                document.body.classList.remove("modal-open");
            }
        });
    });

    // Escape key closes any open modal.
    document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
            if (!overlay.hidden) {
                overlay.hidden = true;
                document.body.classList.remove("modal-open");
            }
        });
    });

    // "+ Create New Category" reveals a text field for the new name.
    var categorySelect = document.getElementById("expense-category-select");
    var newCategoryField = document.getElementById("expense-new-category-field");
    if (categorySelect && newCategoryField) {
        categorySelect.addEventListener("change", function () {
            var showField = categorySelect.value === "__new__";
            newCategoryField.hidden = !showField;
            var input = newCategoryField.querySelector("input");
            if (showField && input) {
                input.setAttribute("required", "required");
                input.focus();
            } else if (input) {
                input.removeAttribute("required");
            }
        });
    }
});
