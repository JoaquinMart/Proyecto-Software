// Comportamiento mínimo del layout (sin dependencias).

// Abrir/cerrar el menú lateral en pantallas chicas
const btnMenu = document.querySelector("[data-toggle-sidebar]");
function setSidebar(abierto) {
  document.body.classList.toggle("sidebar-open", abierto);
  btnMenu?.setAttribute("aria-expanded", String(abierto));
}
btnMenu?.addEventListener("click", () =>
  setSidebar(!document.body.classList.contains("sidebar-open")));
document.querySelector("[data-close-sidebar]")?.addEventListener("click", () => setSidebar(false));

// Cerrar mensajes flash
document.querySelectorAll("[data-close-flash]").forEach((btn) =>
  btn.addEventListener("click", () => btn.closest(".flash").remove()));

// Cerrar el menú de cuenta al hacer click afuera o con Escape
const cuenta = document.querySelector(".account");
document.addEventListener("click", (e) => {
  if (cuenta?.open && !cuenta.contains(e.target)) cuenta.open = false;
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (cuenta) cuenta.open = false;
  setSidebar(false);
});
