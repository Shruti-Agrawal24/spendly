// profile.js — Edit / Cancel toggle for editable cards on the
// Account & Settings page. Self-contained IIFE; no global pollution.
(function () {
    'use strict';

    function findButtons(card) {
        return card.querySelectorAll('[data-edit-trigger]');
    }

    function setEditing(card, isEditing) {
        card.classList.toggle('is-editing', isEditing);
        var buttons = findButtons(card);
        buttons.forEach(function (btn) {
            var label = isEditing ? btn.dataset.editLabelActive : btn.dataset.editLabel;
            if (label) btn.textContent = label;
            btn.setAttribute('aria-pressed', isEditing ? 'true' : 'false');
        });
        var saveBtn = card.querySelector('[data-edit-save]');
        if (saveBtn) {
            saveBtn.hidden = !isEditing;
        }
    }

    function init() {
        var cards = document.querySelectorAll('[data-edit-card]');
        cards.forEach(function (card) {
            var triggers = findButtons(card);
            triggers.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var willEdit = !card.classList.contains('is-editing');
                    setEditing(card, willEdit);
                });
            });
            // Start in view mode.
            setEditing(card, false);
        });

        var deleteBtn = document.querySelector('[data-delete-account]');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function (event) {
                event.preventDefault();
                // TODO: real deletion flow not implemented yet.
                window.alert('Account deletion is not implemented yet. This is a placeholder.');
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
