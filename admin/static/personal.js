// Formulario de personal: el sector solo aplica (y es obligatorio) para Personal Fijo.
const form = document.querySelector("[data-form-persona]");

if (form) {
  const tipo = form.querySelector("#tipo_personal_id");
  const campoSector = form.querySelector("[data-campo-sector]");
  const sector = form.querySelector("#sector_id");

  function actualizar() {
    const codigo = tipo.selectedOptions[0]?.dataset.codigo;
    const esResidente = codigo === "residente";
    campoSector.hidden = esResidente || !codigo;
    sector.required = !esResidente && !!codigo;
    if (esResidente) sector.value = "";
  }

  tipo.addEventListener("change", actualizar);
  actualizar();
}
