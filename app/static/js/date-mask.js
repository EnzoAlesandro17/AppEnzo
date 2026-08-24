document.addEventListener("input", function (event) {
  if (event.target.matches("[data-date-mask]")) {
    var digits = event.target.value.replace(/\D/g, "").slice(0, 8);
    var parts = [];
    if (digits.length > 0) parts.push(digits.slice(0, 2));
    if (digits.length > 2) parts.push(digits.slice(2, 4));
    if (digits.length > 4) parts.push(digits.slice(4, 8));
    event.target.value = parts.join("-");
    return;
  }
  if (event.target.matches("[data-time-mask]")) {
    var digits = event.target.value.replace(/\D/g, "").slice(0, 4);
    var parts = [];
    if (digits.length > 0) parts.push(digits.slice(0, 2));
    if (digits.length > 2) parts.push(digits.slice(2, 4));
    event.target.value = parts.join(":");
    return;
  }
});
