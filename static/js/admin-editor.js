/* @license magnet:?xt=urn:btih:1f739d935676111cfff4b4693e3816e664797050&dn=gpl-3.0.txt GPL-3.0-or-later */
/**
 * Copyright (C) 2026 عباس داورپناه
 *
 * Boots Editor.js on the admin compose page.
 */
(function () {
  var bootEl = document.getElementById("editor-boot");
  if (!bootEl || typeof EditorJS === "undefined") {
    return;
  }

  var boot = JSON.parse(bootEl.textContent || "{}");
  var editor = new EditorJS({
    holder: "editorjs",
    autofocus: false,
    placeholder: "اینجا بنویس؛ با + نوع بلوک را عوض کن",
    data: boot.data || { blocks: [] },
    i18n: {
      direction: "rtl",
      messages: {
        ui: {
          blockTunes: { toggler: { "Click to tune": "تنظیم بلوک", "or drag to move": "یا بکش برای جابه‌جایی" } },
          inlineToolbar: { converter: { "Convert to": "تبدیل به" } },
          toolbar: { toolbox: { Add: "افزودن بلوک" } }
        },
        toolNames: {
          Text: "پاراگراف",
          Heading: "تیتر",
          List: "فهرست",
          Quote: "نقل‌قول",
          Delimiter: "جداکننده",
          Image: "تصویر",
          Bold: "پررنگ",
          Italic: "کج",
          Link: "پیوند",
          "Inline Code": "کد"
        },
        tools: {
          link: { "Add a link": "افزودن پیوند" },
          stub: { "The block can not be displayed correctly.": "این بلوک درست نمایش داده نمی‌شود." }
        },
        blockTunes: {
          delete: { Delete: "حذف", "Click to delete": "برای حذف کلیک کن" },
          moveUp: { "Move up": "انتقال به بالا" },
          moveDown: { "Move down": "انتقال به پایین" }
        }
      }
    },
    tools: {
      paragraph: { class: Paragraph, inlineToolbar: ["link", "bold", "italic"] },
      header: { class: Header, inlineToolbar: ["link", "bold"], config: { levels: [2, 3], defaultLevel: 2, placeholder: "تیتر" } },
      list: { class: List, inlineToolbar: true },
      quote: { class: Quote, inlineToolbar: true, config: { quotePlaceholder: "نقل‌قول", captionPlaceholder: "منبع" } },
      delimiter: Delimiter,
      image: {
        class: ImageTool,
        config: {
          endpoints: { byFile: boot.upload },
          captionPlaceholder: "شرح تصویر"
        }
      }
    }
  });

  editor.isReady.then(function () {
    document.querySelectorAll(".block-palette [data-block]").forEach(function (btn) {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        var type = btn.getAttribute("data-block");
        if (type === "header") {
          editor.blocks.insert("header", { text: "", level: 2 });
        } else if (type === "list") {
          editor.blocks.insert("list", { style: "unordered", items: [""] });
        } else {
          editor.blocks.insert(type);
        }
      });
    });
  });

  var form = document.querySelector(".admin-form");
  var saving = false;
  if (!form) {
    return;
  }
  form.addEventListener("submit", function (event) {
    if (saving) {
      return;
    }
    event.preventDefault();
    editor.save().then(function (output) {
      document.getElementById("body-editor").value = JSON.stringify(output);
      saving = true;
      HTMLFormElement.prototype.submit.call(form);
    });
  });
})();
/* @license-end */
