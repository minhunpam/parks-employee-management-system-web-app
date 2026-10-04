export function renderEmployeeRows(rows, escapeHtml) {
  return rows.map((row, index) => {
    const [day, month, year] = row.date.split(".").map(Number);
    const date = new Date(year, month - 1, day);
    const firstDay = new Date(year, month - 1, 1);
    const mondayOffset = (firstDay.getDay() + 6) % 7;
    const weekNumber = Math.floor((day - 1 + mondayOffset) / 7) + 1;
    const isWeekEnd = date.getDay() === 0 || day === new Date(year, month, 0).getDate();

    const dailyRow = `
      <tr class="border-b border-[#cccccc] last:border-0 hover:bg-[#f7f7f7]">
        <th scope="row" class="px-4 py-4 font-bold">${escapeHtml(row.date)}</th>
        <td class="px-2 py-4">${escapeHtml(row.shiftStart)}</td>
        <td class="px-4 py-4">${escapeHtml(row.pauseStart)}</td>
        <td class="px-4 py-4">${escapeHtml(row.pauseEnd)}</td>
        <td class="px-4 py-4">${escapeHtml(row.shiftEnd)}</td>
        <td class="px-4 py-4">${escapeHtml(row.pauseTime)}</td>
        <td class="px-4 py-4">${escapeHtml(row.shiftTotalTime)}</td>
        <td class="px-4 py-4">${escapeHtml(row.type)}</td>
        <td class="px-4 py-4 ${row.warnings !== "—" ? "font-bold text-[#df6500]" : "text-[#757575]"}">${escapeHtml(row.warnings)}</td>
        <td class="px-4 py-4">
          <button type="button" data-row-index="${index}" class="correct-entry whitespace-nowrap text-sm font-bold text-[#0046a4] underline hover:text-black focus:outline-none focus:ring-2 focus:ring-[#76b900]">
            Correct
          </button>
        </td>
      </tr>`;

    if (!isWeekEnd) return dailyRow;

    return `${dailyRow}
      <tr class="border-b border-[#cccccc] bg-[#f7f7f7]">
        <td colspan="10" class="px-4 py-3 text-lg font-bold text-[#76b900] bg-black text-center">End of week ${weekNumber}</td>
      </tr>`;
  }).join("");
}
