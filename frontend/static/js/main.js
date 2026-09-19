// Symptom selector and dynamic chips bank
document.addEventListener('DOMContentLoaded', () => {
  const symptomInput = document.getElementById('symptoms');
  const chipContainer = document.getElementById('symptomChips');
  if (chipContainer && typeof commonSymptomsBank !== 'undefined') {
    chipContainer.innerHTML = commonSymptomsBank.slice(0, 10).map(s => `
      <button type="button" class="chip" data-symptom="${s.label}">
        <i data-lucide="${s.icon}"></i> ${s.label}
      </button>
    `).join('');
  }
});

// Theme switcher
const themeToggleBtn = document.getElementById('themeToggleBtn');
if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', () => {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    document.documentElement.setAttribute('data-theme', isLight ? 'dark' : 'light');
  });
}
