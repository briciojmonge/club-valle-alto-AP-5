// JavaScript mínimo (mejora progresiva): la plataforma funciona sin él.
(function () {
  "use strict";

  // Confirmación antes de acciones destructivas: <button data-confirmar="¿Seguro?">
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-confirmar]");
    if (btn && !window.confirm(btn.getAttribute("data-confirmar"))) {
      ev.preventDefault();
    }
  });

  // Botones «Imprimir»: <button type="button" data-imprimir> (la CSP no permite onclick en línea).
  document.addEventListener("click", function (ev) {
    if (ev.target.closest("[data-imprimir]")) { window.print(); }
  });

  // Ventanas modales (<dialog>): abrir con data-modal="id", cerrar con data-cerrar o clic fuera.
  document.addEventListener("click", function (ev) {
    var abrir = ev.target.closest("[data-modal]");
    if (abrir) {
      var d = document.getElementById(abrir.getAttribute("data-modal"));
      if (d && d.showModal) { d.showModal(); var f = d.querySelector("input:not([type=hidden]):not([readonly]), select, textarea"); if (f) { f.focus(); } }
      return;
    }
    if (ev.target.closest("[data-cerrar]")) { var m = ev.target.closest("dialog"); if (m) { m.close(); } return; }
    if (ev.target.tagName === "DIALOG") { ev.target.close(); }
  });

  // Rubro de pago: al elegir un rubro se muestra su monto (<option data-monto="...">).
  document.addEventListener("change", function (ev) {
    var sel = ev.target;
    if (sel.matches && sel.matches("select[data-monto-destino]")) {
      var op = sel.options[sel.selectedIndex];
      var dest = document.getElementById(sel.getAttribute("data-monto-destino"));
      if (dest && op) { dest.value = op.getAttribute("data-monto") || ""; }
      var base = sel.getAttribute("data-accion-base");   // el formulario de pago apunta al cargo elegido
      if (base && sel.form) { sel.form.action = base.replace(/\/0\//, "/" + sel.value + "/"); }
    }
  });

  // Actualización automática de la página de ocupación en tiempo real (cada 60 s si se activa).
  var auto = document.getElementById("auto-actualizar");
  if (auto) {
    var temporizador = null;
    var aplicar = function () {
      if (temporizador) { clearInterval(temporizador); temporizador = null; }
      try { window.localStorage.setItem("cva-auto", auto.checked ? "1" : "0"); } catch (e) { /* sin almacenamiento */ }
      if (auto.checked) { temporizador = setInterval(function () { window.location.reload(); }, 60000); }
    };
    try { auto.checked = window.localStorage.getItem("cva-auto") === "1"; } catch (e) { /* sin almacenamiento */ }
    auto.addEventListener("change", aplicar);
    aplicar();
  }

  // Al cambiar de instalación en el formulario de reserva, recarga las franjas disponibles.
  var selInst = document.getElementById("instalacion_id_selector");
  if (selInst && selInst.form && selInst.form.getAttribute("data-recargar") === "1") {
    selInst.addEventListener("change", function () {
      var u = new URL(window.location.href);
      u.searchParams.set("instalacion_id", selInst.value);
      window.location.href = u.toString();
    });
  }
})();
// Selects con data-autoenviar envían su formulario al cambiar (mejora progresiva; sin JS queda el botón de <noscript>).
document.addEventListener("change", function (ev) {
  var s = ev.target;
  if (s.matches && s.matches("select[data-autoenviar]") && s.form) { s.form.submit(); }
});
// Campos de fecha con data-autoenviar-input envían el formulario al elegir una fecha.
document.addEventListener("change", function (ev) {
  var c = ev.target;
  if (c.matches && c.matches("input[data-autoenviar-input]") && c.form && c.value) { c.form.submit(); }
});
