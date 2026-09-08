import { csrfToken, htmlInjectionProtection } from "../common.js";

const page = document.querySelector("#pdf-export-page");
const urls = {
  status: page.dataset.statusUrl,
  generate: page.dataset.generateUrl,
  confirm: page.dataset.confirmUrl,
  sendSummary: page.dataset.sendSummaryUrl,
  sendEmployees: page.dataset.sendEmployeesUrl,
  reconnect: page.dataset.reconnectUrl,
};

const state = {
  batch: null,
  confirmed: false,
  reviewed: false,
  isSending: false,
};

const exportNotice = document.querySelector("#export-notice");
const exportNoticeTitle = document.querySelector("#export-notice-title");
const exportNoticeMessage = document.querySelector("#export-notice-message");
const reconnectGoogle = document.querySelector("#reconnect-google");

const periodTitle = document.querySelector("#period-title");
const readinessStatus = document.querySelector("#readiness-status");
const batchStatus = document.querySelector("#batch-status");

const generateButton = document.querySelector("#generate-button");
const generationStatus = document.querySelector("#generation-status");

const managerRecipientList = document.querySelector("#manager-recipient-list");
const managerRecipientSetupLink = document.querySelector("#manager-recipient-setup-link");

const summaryEmpty = document.querySelector("#summary-empty");
const summaryReviewContainer = document.querySelector("#summary-review-container");
const summaryDownloadLink = document.querySelector("#summary-download-link");
const summaryReviewCheckbox = document.querySelector("#summary-review-checkbox");

const confirmButton = document.querySelector("#confirm-button");

const reviewStatus = document.querySelector("#review-status");
const employeeReportEmpty = document.querySelector("#employee-report-empty");
const employeeReportList = document.querySelector("#employee-report-list");
const employeeReportBody = document.querySelector("#employee-report-body");
const sendSummaryButton = document.querySelector("#send-summary-button");
const sendEmployeesButton = document.querySelector("#send-employees-button");
const summaryDeliveryStatus = document.querySelector("#summary-delivery-status");
const employeeDeliveryStatus = document.querySelector("#employee-delivery-status");

function setNotice(title, message, { reconnect = false, error = false } = {})
{
  exportNotice.hidden = !title && !message;
  exportNoticeTitle.textContent = title || "";
  exportNoticeMessage.textContent = message || "";
  
  exportNotice.classList.toggle("border-[#df6500]", !error);
  exportNotice.classList.toggle("bg-[#feeeb2]", !error);
  exportNotice.classList.toggle("border-[#e52020]", error);
  exportNotice.classList.toggle("bg-[#ffe5e5]", error);
  
  reconnectGoogle.hidden = !reconnect;
  reconnectGoogle.href = urls.reconnect || "#";
}


function statusLabel(value, fallback = "Not available") {
    return String(value || fallback).replaceAll("_", " ");
}

function statusClass(value) {
    const normalized = String(value || "").toLowerCase();
    if (["sent", "generated", "confirmed", "ready", "success"].includes(normalized)) {
        return "text-[#3f8500]";
    }
    if (["failed", "error", "blocked"].includes(normalized)) {
        return "font-bold text-[#e52020]";
    }
    return "text-[#757575]";
}

async function loadStatus() {
  readinessStatus.textContent = "Checking export readiness…";
  try {
    const data = await requestJson(urls.status);
    renderBatch(data);

    if (data.code === "google_reconnect_required") {
      setNotice(
        "Reconnect Google is required",
        data.error,
        { reconnect: true });
    } else {
      setNotice();
    }
  } catch (error) {
    readinessStatus.textContent = error.message;
    setNotice("Export status unavailable", error.message, { error: true });
  } finally {
    setButtons();
  }
}

async function requestJson(url, options = {}) {
  if (!url) {
    throw new Error("This action is not configured yet.");
  }

  const response = await fetch(url, {
      ...options,
      headers: {
          Accept: "application/json",
          ...(options.body ? { "Content-Type": "application/json", "X-CSRFToken": csrfToken() } : {}),
          ...(options.headers || {}),
      },
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
      const error = new Error(payload.error || payload.message || "The request could not be completed.");
      error.code = payload.code;
      throw error;
  }

  return payloadData(payload);
}

function payloadData(payload) {
    return payload?.data || payload || {};
}

function renderBatch(data) {
  state.batch = data;
  state.confirmed = Boolean(data.confirmed);
  state.reviewed = Boolean(data.reviewed || state.reviewed);

  periodTitle.textContent = data.period_label || data.configuration_period || "Configured month";
  readinessStatus.textContent = data.readiness_message || (data.ready === false
      ? "Export is blocked until the month is ready."
      : "The month is ready for export.");

  batchStatus.textContent = statusLabel(data.batch_status, data.summary_pdf_url ? "PDFs generated" : "No export generated");
  batchStatus.className = `inline-flex items-center self-start border px-3 py-2 text-xs font-bold uppercase tracking-wide ${statusClass(data.batch_status)}`;

  generationStatus.textContent = data.generation_message || "";

  renderRecipients(data.manager_recipients || []);

  if (data.summary_pdf_url) {
    summaryEmpty.hidden = true;
    summaryReviewContainer.hidden = false;
    summaryDownloadLink.href = data.summary_pdf_url;
    reviewStatus.textContent = state.confirmed ? "Review confirmed" : "Review required";
    reviewStatus.className = `border px-3 py-2 text-xs font-bold uppercase tracking-wide ${state.confirmed ? "border-[#3f8500] text-[#3f8500]" : "border-[#cccccc] text-[#757575]"}`;

    summaryReviewCheckbox.disabled = state.confirmed;
    summaryReviewCheckbox.checked = state.confirmed;
    
  } else {
    summaryEmpty.hidden = false;
    summaryReviewContainer.hidden = true;
    summaryDownloadLink.href = "#";
    reviewStatus.textContent = "Review required";
  }

  renderEmployeeReports(data.employee_reports || []);

  const summaryDelivery = data.summary_delivery || {};
  summaryDeliveryStatus.textContent = state.confirmed ? "Ready to send to configured managers." : "Review and confirm the summary first.";
  if (summaryDelivery.status === "sent") {
    summaryDeliveryStatus.textContent = "Delivery finished"
  }
  
  const employeeDelivery = data.employee_delivery || {};
  employeeDeliveryStatus.textContent = state.confirmed ? "Ready to send employee PDFs." : "Review and confirm the summary first.";
  if (employeeDelivery.status === "sent") {
    employeeDeliveryStatus.textContent = "Delivery finished"
  }
  
  setButtons();
}

function renderRecipients(recipients = []) {
    if (!recipients.length) {
        managerRecipientList.innerHTML = '<li class="py-3 text-[#e52020]">No manager recipients configured.</li>';
        managerRecipientSetupLink.hidden = false;
        return;
    }

    managerRecipientSetupLink.hidden = true;
    managerRecipientList.innerHTML = recipients.map((recipient) =>
        `<li class="break-all py-3">${htmlInjectionProtection(recipient)}</li>`
    ).join("");
}

function renderEmployeeReports(reports = []) {
    employeeReportEmpty.hidden = reports.length !== 0;
    employeeReportList.hidden = reports.length === 0;

    employeeReportBody.innerHTML = reports.map((report) => {
      const pdfLink = report.pdf_url
        ? `<a href="${htmlInjectionProtection(report.pdf_url)}" target="_blank" rel="noopener" class="font-bold text-[#0046a4] underline hover:text-black">
          Open PDF
        `
        : "—";
      const details = report.error || report.delivery_error || "—";
      
      return `
      <tr class="border-b border-[#cccccc] last:border-0 hover:bg-[#f7f7f7]">
        <th scope="row" class="px-4 py-4 font-bold">
          ${htmlInjectionProtection(report.employee || report.name)}
        </th>
        <td class="px-4 py-4">${pdfLink}</td>
        <td class="px-4 py-4 ${statusClass(report.generation_status)}">
          ${htmlInjectionProtection(statusLabel(report.generation_status))}
        </td>
        <td class="px-4 py-4 ${statusClass(report.delivery_status)}">
          ${htmlInjectionProtection(statusLabel(report.delivery_status, "Not sent"))}
        </td>
        <td class="max-w-xs px-4 py-4 text-[#757575]">
          ${htmlInjectionProtection(details)}
        </td>
      </tr>`;
    }).join("");
}

function setButtons() {
  const hasSummary = Boolean(state.batch?.summary_pdf_url);
  const exportReady = state.batch?.ready !== false;

  const summaryAlreadySent =
    state.batch?.summary_delivery?.status === "sent";

  const employeesAlreadySent =
    state.batch?.employee_delivery?.status === "sent";

  generateButton.disabled =
    state.isSending ||
    !urls.generate ||
    !exportReady;

  confirmButton.disabled =
    !hasSummary ||
    !state.reviewed ||
    state.confirmed ||
    !urls.confirm;

  sendSummaryButton.disabled =
    state.isSending ||
    !state.confirmed ||
    !urls.sendSummary ||
    summaryAlreadySent;

  sendEmployeesButton.disabled =
    state.isSending ||
    !state.confirmed ||
    !urls.sendEmployees ||
    employeesAlreadySent;
}

async function generateReports() {
  generateButton.disabled = true;
  generationStatus.textContent = "Generating PDFs…";
  state.batch = null;
  state.confirmed = false;
  state.reviewed = false;
  summaryReviewCheckbox.checked = false;

  try {
      const data = await requestJson(urls.generate, { method: "POST", body: JSON.stringify({}) });
      renderBatch(data);
      setNotice();
  } catch (error) {
      generationStatus.textContent = error.message;
      setNotice("PDF generation failed", error.message, { error: true });
  } finally {
      setButtons();
  }
}

async function confirmReview() {
  confirmButton.disabled = true;
  reviewStatus.textContent = "Saving confirmation…";
  
  try {
    const data = await requestJson(urls.confirm, {
      method: "POST",
      body: JSON.stringify({ reviewed: true })
    });
    
    state.confirmed = true;
    renderBatch({ ...state.batch, ...data, confirmed: true, reviewed: true });
    setNotice();
  } catch (error) {
      reviewStatus.textContent = error.message;
      setNotice("Confirmation failed", error.message, { error: true });
  } finally {
      setButtons();
  }
}

async function sendReports(url, statusElement, message) {
  state.isSending = true;
  setButtons();
  
  statusElement.textContent = `${message}...`;

  try {
    const data = await requestJson(url, {
      method: "POST",
      body: JSON.stringify({})
    });

    renderBatch({
      ...state.batch,
      ...data,
      confirmed: true
    });
    statusElement.textContent = data.message || "Delivery completed";
    setNotice();
  } catch (error) {
    statusElement.textContent = error.message;
    setNotice("Delivery finished with an error", error.message, { error: true });
  } finally {
    state.isSending = false;
    setButtons();
  }
}

summaryReviewCheckbox.addEventListener("change", () => {
  state.reviewed = summaryReviewCheckbox.checked;
  setButtons();
});


generateButton.addEventListener("click", generateReports);
confirmButton.addEventListener("click", confirmReview);
sendSummaryButton.addEventListener("click", () =>
{
  sendReports(
    urls.sendSummary,
    summaryDeliveryStatus,
    "Sending summary to managers"
  )
});

sendEmployeesButton.addEventListener("click", () =>
{
  sendReports(
    urls.sendEmployees,
    employeeDeliveryStatus,
    "Sending employee PDFs"
  )
});

loadStatus();
