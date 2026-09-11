const monthYearDisplayer = document.querySelector("#month-year-displayer");

const today = new Date();
const year = today.getFullYear();
const month = today.toLocaleString('default', { month: 'long' });
monthYearDisplayer.textContent = `${month} ${year}`
