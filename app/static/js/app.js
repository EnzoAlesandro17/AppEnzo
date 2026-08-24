document.addEventListener("change", function (event) {
  if (event.target.matches("[data-autosubmit]")) {
    event.target.form.submit();
  }
});

document.addEventListener(
  "blur",
  function (event) {
    if (event.target.matches("[data-autosubmit-blur]")) {
      var initial = event.target.defaultValue;
      if (event.target.value !== initial && event.target.value.trim() !== "") {
        event.target.form.submit();
      }
    }
  },
  true
);
