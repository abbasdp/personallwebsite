/* @license magnet:?xt=urn:btih:1f739d935676111cfff4b4693e3816e664797050&dn=gpl-3.0.txt GPL-3.0-or-later */
/**
 * Copyright (C) 2026 عباس داورپناه
 *
 * Repeatable social rows on the site-content admin form.
 */
(function () {
  document.addEventListener("click", function (event) {
    var removeBtn = event.target.closest("[data-remove-row]");
    if (removeBtn) {
      event.preventDefault();
      var row = removeBtn.closest(".repeat-row");
      if (row) {
        row.remove();
      }
      return;
    }

    if (event.target.closest("[data-add-social]")) {
      event.preventDefault();
      var socialTpl = document.getElementById("tpl-social");
      var socials = document.getElementById("socials");
      if (socialTpl && socials) {
        socials.appendChild(socialTpl.content.cloneNode(true));
      }
    }
  });
})();
/* @license-end */
