// Validaciones del formulario de usuario en el cliente.
// Los campos requeridos, formato de correo, nombre, apellido y DNI se validan
// con atributos HTML (required, type="email", pattern, minlength).
// Acá va lo que depende de otros campos. El servidor vuelve a validar todo.

const form = document.querySelector("[data-form-usuario]");

if (form) {
  const rol = form.querySelector("#rol_id");
  const campoSector = form.querySelector("[data-campo-sector]");
  const sector = form.querySelector("#sector_id");
  const activo = form.querySelector("#activo");
  const notaAdmin = form.querySelector("[data-nota-admin]");
  const password = form.querySelector("#password");
  const confirmacion = form.querySelector("#password_confirmacion");
  const confirmacionRequerida = confirmacion.required;

  // Sector visible y obligatorio solo para Jefe de Servicio
  function actualizarRol() {
    const codigo = rol.selectedOptions[0]?.dataset.codigo;
    const esJefe = codigo === "jefe_servicio";
    const esAdmin = codigo === "administrador";

    campoSector.hidden = !esJefe;
    sector.required = esJefe;
    if (!esJefe) sector.value = "";

    notaAdmin.hidden = !esAdmin;
    if (esAdmin) activo.checked = true;
    activo.disabled = esAdmin; // el servidor igual lo fuerza a activo
  }

  // La confirmación tiene que coincidir con la contraseña
  function chequearPassword() {
    confirmacion.required = confirmacionRequerida || password.value !== "";
    const distintas = password.value !== "" && confirmacion.value !== password.value;
    confirmacion.setCustomValidity(distintas ? "Las contraseñas no coinciden." : "");
  }

  rol.addEventListener("change", actualizarRol);
  password.addEventListener("input", chequearPassword);
  confirmacion.addEventListener("input", chequearPassword);
  actualizarRol();
  chequearPassword();
}
