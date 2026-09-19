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
