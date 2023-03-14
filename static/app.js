const dropzone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");
const jobsList = document.getElementById("jobs-list");
const detailPanel = document.getElementById("detail-panel");
const detailTitle = document.getElementById("detail-title");
const tablesContainer = document.getElementById("tables-container");

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragover");
  const [file] = event.dataTransfer.files;
  if (file) uploadFile(file);
});

fileInput.addEventListener("change", () => {
  const [file] = fileInput.files;
  if (file) uploadFile(file);
});

async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/upload", { method: "POST", body: formData });
  if (!response.ok) {
    alert("Falha ao enviar o arquivo.");
    return;
  }
  const { job_id: jobId } = await response.json();
  await pollJob(jobId);
  await refreshHistory();
}

async function pollJob(jobId) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const response = await fetch(`/api/job/${jobId}/status`);
    const job = await response.json();
    if (job.status === "completed" || job.status === "failed") return job;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return null;
}

async function refreshHistory() {
  const response = await fetch("/api/history");
  const jobs = await response.json();
  jobsList.innerHTML = "";

  jobs.forEach((job) => {
    const item = document.createElement("li");
    item.className = `job job--${job.status}`;

    const label = document.createElement("span");
    label.textContent = `${job.original_filename} · ${job.status} · ${job.table_count} tabela(s)`;
    item.appendChild(label);

    const viewButton = document.createElement("button");
    viewButton.textContent = "Ver tabelas";
    viewButton.disabled = job.status !== "completed";
    viewButton.addEventListener("click", () => showJobDetail(job.id));
    item.appendChild(viewButton);

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Excluir";
    deleteButton.addEventListener("click", async () => {
      await fetch(`/api/job/${job.id}`, { method: "DELETE" });
      await refreshHistory();
    });
    item.appendChild(deleteButton);

    jobsList.appendChild(item);
  });
}

async function showJobDetail(jobId) {
  const response = await fetch(`/api/job/${jobId}/tables`);
  const job = await response.json();

  detailPanel.hidden = false;
  detailTitle.textContent = job.original_filename;
  tablesContainer.innerHTML = "";

  job.tables.forEach((table) => {
    const wrapper = document.createElement("div");
    wrapper.className = "table-card";

    const caption = document.createElement("p");
    caption.textContent = `Página ${table.page_number} · confiança ${(table.confidence * 100).toFixed(0)}%`;
    wrapper.appendChild(caption);

    const html = document.createElement("table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    table.headers.forEach((header) => {
      const th = document.createElement("th");
      th.textContent = header;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    html.appendChild(thead);

    const tbody = document.createElement("tbody");
    table.rows.forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((cell) => {
        const td = document.createElement("td");
        td.textContent = cell ?? "";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    html.appendChild(tbody);
    wrapper.appendChild(html);

    const exportButton = document.createElement("button");
    exportButton.textContent = "Exportar CSV";
    exportButton.addEventListener("click", () => {
      window.location.href = `/api/job/${jobId}/export/csv?table_id=${table.id}`;
    });
    wrapper.appendChild(exportButton);

    tablesContainer.appendChild(wrapper);
  });

  const exportAllButton = document.createElement("button");
  exportAllButton.textContent = "Exportar tudo (Excel)";
  exportAllButton.addEventListener("click", () => {
    window.location.href = `/api/job/${jobId}/export/xlsx`;
  });
  tablesContainer.appendChild(exportAllButton);
}

refreshHistory();
