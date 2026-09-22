const vehicleData = {
    bike: {
        brands: ['Hero', 'Honda', 'Bajaj', 'TVS', 'Royal Enfield', 'Yamaha', 'Suzuki'],
        models: {
            'Hero': ['Splendor Plus', 'HF Deluxe', 'Passion Pro', 'Glamour', 'Xtreme 160R', 'Pleasure Plus', 'Destini 125'],
            'Honda': ['Activa 6G', 'Activa 125', 'Shine 125', 'SP 125', 'Unicorn', 'Dio 125', 'Hornet 2.0'],
            'Bajaj': ['Pulsar 125', 'Pulsar 150', 'Pulsar NS200', 'Platina 100', 'Platina 110', 'CT 110', 'Avenger 160'],
            'TVS': ['Jupiter 110', 'Jupiter 125', 'Apache RTR 160', 'Apache RTR 180', 'Raider 125', 'XL100', 'Ntorq 125'],
            'Royal Enfield': ['Classic 350', 'Bullet 350', 'Hunter 350', 'Meteor 350'],
            'Yamaha': ['FZ-S V4', 'FZ-X', 'MT-15 V2', 'RayZR 125', 'Fascino 125'],
            'Suzuki': ['Access 125', 'Burgman Street', 'Gixxer 150', 'Avenis 125']
        }
    },
    car: {
        brands: ['Maruti Suzuki', 'Hyundai', 'Tata', 'Mahindra', 'Honda', 'Kia', 'Toyota', 'Renault'],
        models: {
            'Maruti Suzuki': ['WagonR', 'Swift', 'Dzire', 'Baleno', 'Alto K10', 'Brezza', 'Ertiga', 'Fronx', 'Celerio', 'Eeco'],
            'Hyundai': ['Grand i10 Nios', 'i20', 'Venue', 'Creta', 'Exter', 'Aura', 'Verna'],
            'Tata': ['Punch', 'Nexon', 'Tiago', 'Tigor', 'Altroz', 'Harrier'],
            'Mahindra': ['Bolero', 'Bolero Neo', 'Scorpio-Classic', 'Scorpio-N', 'XUV300', 'XUV700', 'Thar'],
            'Honda': ['Amaze', 'City', 'Elevate'],
            'Kia': ['Sonet', 'Seltos', 'Carens'],
            'Toyota': ['Glanza', 'Urban Cruiser Taisor', 'Hyryder', 'Innova Crysta', 'Rumion'],
            'Renault': ['Kwid', 'Triber', 'Kiger']
        }
    },
    cycle: {
        brands: ['Hero Cycles', 'Atlas', 'Avon', 'Hercules', 'BSA', 'Firefox', 'Leader'],
        models: {
            'Hero Cycles': ['Hero Jet / Desi Cycle', 'Hero Sprint Pro', 'Hero Ranger', 'Hero Kyoto', 'Hero Octane', 'Hero Lectro (Electric)'],
            'Atlas': ['Atlas Goldline', 'Atlas Ultimate', 'Atlas Camp', 'Atlas Motion'],
            'Avon': ['Avon Prime', 'Avon Steed', 'Avon Elements', 'Avon Buke MTB'],
            'Hercules': ['Hercules Roadeo Hardliner', 'Hercules Turbodrive', 'Hercules Streetcat', 'Hercules Captain'],
            'BSA': ['BSA Ladybird', 'BSA Champ', 'BSA SLR', 'BSA Photon'],
            'Firefox': ['Firefox Target', 'Firefox Mount 29', 'Firefox Bad Attitude'],
            'Leader': ['Leader Scout MTB', 'Leader Beast', 'Leader Gladiator']
        }
    }
};

const baselineCosts = {
    bike: {
        'Starting System': [800, 1600],
        'Brake System': [600, 1400],
        'Engine': [2500, 7500],
        'Battery/Electrical': [1200, 2200],
        'Suspension': [900, 2000],
        'Cooling System': [1200, 2500],
        'Fuel System': [700, 1500],
        'Transmission': [1500, 3200],
        'Tyres/Wheels': [900, 1800],
        'General Maintenance': [500, 1200]
    },
    car: {
        'Starting System': [2200, 4500],
        'Brake System': [2200, 5500],
        'Engine': [4000, 12000],
        'Battery/Electrical': [3500, 7000],
        'Suspension': [4500, 9500],
        'Cooling System': [2500, 5000],
        'Fuel System': [2000, 4800],
        'Transmission': [6000, 15000],
        'Tyres/Wheels': [1500, 3500],
        'General Maintenance': [2500, 4500]
    },
    cycle: {
        'Starting System': [100, 250],
        'Brake System': [100, 350],
        'Engine': [150, 400],
        'Battery/Electrical': [150, 500],
        'Suspension': [200, 600],
        'Cooling System': [100, 250],
        'Fuel System': [100, 250],
        'Transmission': [150, 450],
        'Tyres/Wheels': [120, 350],
        'General Maintenance': [150, 350]
    }
};

let currentUser = null;
let currentRecordId = null;
let selectedRating = 0;
let categoryChart = null;
let urgencyChart = null;

document.addEventListener('DOMContentLoaded', () => {
    // Theme Switcher (Light / Night Mode)
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeToggleIcon = document.getElementById('themeToggleIcon');
    const savedTheme = localStorage.getItem('servicewise_theme') || 'dark';

    function applyTheme(theme) {
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
            if (themeToggleIcon) {
                themeToggleIcon.setAttribute('data-lucide', 'moon');
                themeToggleIcon.style.color = '#6366f1';
            }
        } else {
            document.documentElement.removeAttribute('data-theme');
            if (themeToggleIcon) {
                themeToggleIcon.setAttribute('data-lucide', 'sun');
                themeToggleIcon.style.color = '#f59e0b';
            }
        }
        localStorage.setItem('servicewise_theme', theme);
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }

    applyTheme(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            applyTheme(newTheme);
        });
    }

    const typeSelect = document.getElementById('vehicle_type');
    const brandSelect = document.getElementById('vehicle_brand');
    const modelSelect = document.getElementById('vehicle_model');
    const form = document.getElementById('assessmentForm');
    const submitBtn = document.getElementById('submitBtn');
    const loading = document.getElementById('loadingIndicator');
    const resultArea = document.getElementById('resultArea');
    const formError = document.getElementById('formError');

    // Check initial auth state
    checkAuthSession();

    // Cascading Vehicle Selects
    typeSelect.addEventListener('change', function() {
        brandSelect.innerHTML = '<option value="">Select brand&hellip;</option>';
        modelSelect.innerHTML = '<option value="">Select model&hellip;</option>';
        modelSelect.disabled = true;

        if (this.value && vehicleData[this.value]) {
            brandSelect.disabled = false;
            vehicleData[this.value].brands.forEach(brand => {
                const opt = document.createElement('option');
                opt.value = brand;
                opt.textContent = brand;
                brandSelect.appendChild(opt);
            });
        } else {
            brandSelect.disabled = true;
        }
    });

    brandSelect.addEventListener('change', function() {
        modelSelect.innerHTML = '<option value="">Select model&hellip;</option>';
        const type = typeSelect.value;
        if (this.value && type && vehicleData[type] && vehicleData[type].models[this.value]) {
            modelSelect.disabled = false;
            vehicleData[type].models[this.value].forEach(model => {
                const opt = document.createElement('option');
                opt.value = model;
                opt.textContent = model;
                modelSelect.appendChild(opt);
            });
        } else {
            modelSelect.disabled = true;
        }
    });

    // Symptom Chips Shortcut Fill
    function setupChipListeners() {
        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const symptomText = chip.getAttribute('data-symptom');
                const textarea = document.getElementById('symptoms');
                textarea.value = symptomText;

                // Auto-fill fallback vehicle defaults if empty for quick test
                if (!typeSelect.value) {
                    typeSelect.value = 'bike';
                    typeSelect.dispatchEvent(new Event('change'));
                    setTimeout(() => {
                        brandSelect.value = 'Hero';
                        brandSelect.dispatchEvent(new Event('change'));
                        setTimeout(() => {
                            modelSelect.value = 'Splendor Plus';
                        }, 50);
                    }, 50);
                }
                if (!document.getElementById('vehicle_age').value) {
                    document.getElementById('vehicle_age').value = '3';
                }
                if (!document.getElementById('km_driven').value) {
                    document.getElementById('km_driven').value = '25000';
                }
            });
        });
    }
    setupChipListeners();

    // Toggle More Symptom Shortcut Chips
    const toggleMoreChipsBtn = document.getElementById('toggleMoreChipsBtn');
    const moreChipsLabel = document.getElementById('moreChipsLabel');
    const moreChipsIcon = document.getElementById('moreChipsIcon');

    if (toggleMoreChipsBtn) {
        let isExpanded = false;
        toggleMoreChipsBtn.addEventListener('click', () => {
            isExpanded = !isExpanded;
            document.querySelectorAll('.chip.extra-chip').forEach(chip => {
                chip.style.display = isExpanded ? 'inline-flex' : 'none';
            });
            if (moreChipsLabel) moreChipsLabel.textContent = isExpanded ? 'Show Less' : 'Show More Shortcuts';
            if (moreChipsIcon) moreChipsIcon.setAttribute('data-lucide', isExpanded ? 'chevron-up' : 'chevron-down');
            if (typeof lucide !== 'undefined' && lucide.createIcons) {
                lucide.createIcons();
            }
        });
    }

    // Smart 100+ Symptoms Autocomplete & Keyword Search Dropdown
    const symptomsTextarea = document.getElementById('symptoms');
    const dropdown = document.getElementById('symptomSuggestionsDropdown');

    if (symptomsTextarea && dropdown && typeof commonSymptomsBank !== 'undefined') {
        symptomsTextarea.addEventListener('input', (e) => {
            const query = e.target.value.trim().toLowerCase();
            if (query.length < 2) {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
                return;
            }

            // Search by keywords or label
            const matches = commonSymptomsBank.filter(s => {
                const labelMatch = s.label.toLowerCase().includes(query);
                const kwMatch = s.keywords && s.keywords.some(k => k.toLowerCase().includes(query) || query.includes(k.toLowerCase()));
                const catMatch = s.category.toLowerCase().includes(query);
                return labelMatch || kwMatch || catMatch;
            }).slice(0, 6);

            if (matches.length === 0) {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
                return;
            }

            dropdown.innerHTML = matches.map(m => `
                <div class="symptom-dropdown-item" data-text="${m.label.replace(/"/g, '&quot;')}">
                    <i data-lucide="${m.icon || 'alert-circle'}" style="width:14px;height:14px;color:var(--accent);flex-shrink:0;"></i>
                    <span style="flex:1;">${m.label}</span>
                    <span style="font-size:0.75rem;font-weight:600;color:var(--success,#10b981);background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.25);border-radius:4px;padding:2px 6px;white-space:nowrap;">${m.price || '₹300 - ₹1,500'}</span>
                    <span class="symptom-category-tag">${m.category}</span>
                </div>
            `).join('');

            dropdown.style.display = 'block';
            if (typeof lucide !== 'undefined' && lucide.createIcons) {
                lucide.createIcons();
            }

            dropdown.querySelectorAll('.symptom-dropdown-item').forEach(item => {
                item.addEventListener('click', () => {
                    const chosenText = item.getAttribute('data-text');
                    symptomsTextarea.value = chosenText;
                    dropdown.style.display = 'none';

                    // Auto-fill fallback vehicle defaults if empty for quick test
                    if (!typeSelect.value) {
                        typeSelect.value = 'bike';
                        typeSelect.dispatchEvent(new Event('change'));
                        setTimeout(() => {
                            brandSelect.value = 'Hero';
                            brandSelect.dispatchEvent(new Event('change'));
                            setTimeout(() => {
                                modelSelect.value = 'Splendor Plus';
                            }, 50);
                        }, 50);
                    }
                    if (!document.getElementById('vehicle_age').value) {
                        document.getElementById('vehicle_age').value = '3';
                    }
                    if (!document.getElementById('km_driven').value) {
                        document.getElementById('km_driven').value = '25000';
                    }
                });
            });
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!symptomsTextarea.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
    }

    // Tab Switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    function switchTab(targetTab) {
        document.querySelectorAll('.tab-btn').forEach(b => {
            b.classList.remove('active');
            b.setAttribute('aria-selected', 'false');
        });
        const activeBtn = document.getElementById(`btn-${targetTab}`);
        if (activeBtn) {
            activeBtn.classList.add('active');
            activeBtn.setAttribute('aria-selected', 'true');
        }

        document.querySelectorAll('[role="tabpanel"]').forEach(panel => {
            panel.style.display = 'none';
        });
        const activePanel = document.getElementById(`tab-${targetTab}`);
        if (activePanel) {
            activePanel.style.display = 'block';
        }

        if (targetTab === 'history') {
            loadHistoryRecords(1);
        } else if (targetTab === 'analytics') {
            loadAnalytics();
        } else if (targetTab === 'metrics') {
            loadMetrics();
        }

        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }

    // Diagnosis Form Submit
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        formError.style.display = 'none';

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        if (!data.vehicle_type || !data.vehicle_brand || !data.vehicle_model || !data.vehicle_age || !data.km_driven || !data.symptoms.trim()) {
            formError.textContent = 'Please fill out all required fields before analyzing.';
            formError.style.display = 'block';
            return;
        }

        data.vehicle_age = parseInt(data.vehicle_age, 10);
        data.km_driven = parseInt(data.km_driven, 10);

        if (data.vehicle_age < 0 || data.vehicle_age > 30) {
            formError.textContent = 'Vehicle age must be between 0 and 30 years.';
            formError.style.display = 'block';
            return;
        }
        if (data.km_driven < 0 || data.km_driven > 500000) {
            formError.textContent = 'Kilometres driven must be between 0 and 5,00,000.';
            formError.style.display = 'block';
            return;
        }

        submitBtn.style.display = 'none';
        loading.style.display = 'block';
        resultArea.style.display = 'none';
        resultArea.style.opacity = '0';

        fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(res => {
            if (!res.ok) return res.json().then(err => { throw new Error(err.error || 'Failed to compute diagnosis.'); });
            return res.json();
        })
        .then(result => {
            currentRecordId = result.record_id;
            document.getElementById('resCategory').textContent = result.problem_category || 'General';
            document.getElementById('resCost').textContent = `₹${Math.round(result.estimated_cost_min).toLocaleString('en-IN')} – ₹${Math.round(result.estimated_cost_max).toLocaleString('en-IN')}`;
            document.getElementById('resRecommendation').textContent = result.recommendation;

            const badge = document.getElementById('urgencyBadge');
            badge.textContent = `Urgency: ${result.urgency}`;
            badge.className = `badge badge-${result.urgency}`;

            // Save pending feedback item in localStorage for prompt on next visit/re-login/reload
            const pendingFeedback = {
                record_id: result.record_id,
                vehicle: `${data.vehicle_brand} ${data.vehicle_model} (${data.vehicle_type})`,
                symptoms: data.symptoms,
                created_at: new Date().toISOString()
            };
            localStorage.setItem('servicewise_pending_feedback', JSON.stringify(pendingFeedback));

            resultArea.style.display = 'block';
            setTimeout(() => {
                resultArea.style.opacity = '1';
                if (typeof lucide !== 'undefined' && lucide.createIcons) {
                    lucide.createIcons();
                }
            }, 50);
        })
        .catch(err => {
            formError.textContent = err.message || 'An error occurred while connecting to the diagnosis server.';
            formError.style.display = 'block';
        })
        .finally(() => {
            submitBtn.style.display = 'flex';
            loading.style.display = 'none';
        });
    });

    // Feedback Stars Selection
    document.querySelectorAll('#starRatingGroup .star').forEach(star => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.getAttribute('data-star'), 10);
            document.querySelectorAll('#starRatingGroup .star').forEach((s, idx) => {
                if (idx < selectedRating) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });
        });
    });

    // Submit Feedback inside Center Modal
    document.getElementById('submitFeedbackBtn').addEventListener('click', () => {
        const notice = document.getElementById('feedbackNotice');
        const targetRecordId = currentRecordId || pendingFeedbackRecordId;

        if (!targetRecordId) {
            notice.textContent = 'No active record found to submit feedback.';
            notice.style.color = 'var(--danger)';
            notice.style.display = 'block';
            return;
        }
        if (selectedRating < 1 || selectedRating > 5) {
            notice.textContent = 'Please select a star rating (1 to 5).';
            notice.style.color = 'var(--danger)';
            notice.style.display = 'block';
            return;
        }

        const actualCostInput = document.getElementById('fbActualCost').value;
        const actualCost = actualCostInput ? parseFloat(actualCostInput) : null;
        const comments = document.getElementById('fbComments').value;

        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_id: targetRecordId,
                accuracy_rating: selectedRating,
                actual_cost: actualCost,
                comments: comments
            })
        })
        .then(res => res.json())
        .then(data => {
            localStorage.removeItem('servicewise_pending_feedback');
            const modal = document.getElementById('feedbackModal');
            if (modal) modal.style.display = 'none';
            showAuthToast('Feedback Received!', 'Thank you! Your actual repair details help calibrate the ML models.', 'success');
        })
        .catch(err => {
            notice.textContent = err.message || 'Error submitting feedback.';
            notice.style.color = 'var(--danger)';
            notice.style.display = 'block';
        });
    });

    // Close & Skip Feedback Modal
    const feedbackModal = document.getElementById('feedbackModal');
    const closeFeedbackModal = document.getElementById('closeFeedbackModal');
    const skipFeedbackBtn = document.getElementById('skipFeedbackBtn');
    let pendingFeedbackRecordId = null;

    if (closeFeedbackModal) {
        closeFeedbackModal.addEventListener('click', () => {
            feedbackModal.style.display = 'none';
        });
    }
    if (skipFeedbackBtn) {
        skipFeedbackBtn.addEventListener('click', () => {
            feedbackModal.style.display = 'none';
        });
    }

    // Check & trigger center feedback prompt on page reload/re-login/revisit
    function checkPendingFeedbackPrompt() {
        try {
            const raw = localStorage.getItem('servicewise_pending_feedback');
            if (!raw) return;
            const item = JSON.parse(raw);
            if (!item || !item.record_id) return;

            pendingFeedbackRecordId = item.record_id;
            const vehicleLabel = document.getElementById('fbModalVehicle');
            const symLabel = document.getElementById('fbModalSymptoms');
            if (vehicleLabel) vehicleLabel.textContent = item.vehicle || 'Recent Vehicle Diagnosis';
            if (symLabel) symLabel.textContent = item.symptoms ? `Issue: "${item.symptoms}"` : 'Diagnostic Assessment';

            // Reset stars & fields
            selectedRating = 0;
            document.querySelectorAll('#starRatingGroup .star').forEach(s => s.classList.remove('active'));
            document.getElementById('fbActualCost').value = '';
            document.getElementById('fbComments').value = '';
            document.getElementById('feedbackNotice').style.display = 'none';

            setTimeout(() => {
                feedbackModal.style.display = 'flex';
                if (typeof lucide !== 'undefined' && lucide.createIcons) {
                    lucide.createIcons();
                }
            }, 800);
        } catch (e) {}
    }

    // Call check on page startup
    checkPendingFeedbackPrompt();

    // Service Records Loader with Pagination
    let currentHistoryPage = 1;
    let historyPerPage = 20;
    let totalHistoryPages = 1;
    let currentHistorySort = 'desc';

    function loadHistoryRecords(page = 1) {
        currentHistoryPage = page;
        const tbody = document.getElementById('historyTableBody');
        const paginationContainer = document.getElementById('historyPagination');
        tbody.innerHTML = '<tr><td colspan="7" style="color:var(--text-muted);text-align:center;padding:2rem;">Loading service records&hellip;</td></tr>';

        fetch(`/api/records?page=${currentHistoryPage}&per_page=${historyPerPage}&sort=${currentHistorySort}`)
            .then(res => res.json())
            .then(data => {
                let records = [];
                let total = 0;
                if (Array.isArray(data)) {
                    records = data;
                    total = data.length;
                    totalHistoryPages = 1;
                } else {
                    records = data.records || [];
                    total = data.total || 0;
                    totalHistoryPages = data.total_pages || 1;
                    currentHistoryPage = data.page || 1;
                }

                if (!records || records.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--text-muted);text-align:center;padding:2rem;">No service records found. Run a diagnosis first!</td></tr>';
                    if (paginationContainer) paginationContainer.style.display = 'none';
                    return;
                }

                tbody.innerHTML = records.map((r) => {
                    let predictedDisplay = '₹1,500 – ₹3,000';
                    let actualDisplay = '—';

                    if (r.actual_cost && !isNaN(r.actual_cost)) {
                        const cost = Math.round(Number(r.actual_cost));
                        const minC = Math.round(cost * 0.85);
                        const maxC = Math.round(cost * 1.15);
                        predictedDisplay = `₹${minC.toLocaleString('en-IN')} – ₹${maxC.toLocaleString('en-IN')}`;
                        actualDisplay = `₹${cost.toLocaleString('en-IN')}`;
                    } else if (r.predicted_cost_min && r.predicted_cost_max) {
                        predictedDisplay = `₹${Math.round(r.predicted_cost_min).toLocaleString('en-IN')} – ₹${Math.round(r.predicted_cost_max).toLocaleString('en-IN')}`;
                    }

                    return `
                    <tr>
                        <td class="mono" style="color:var(--text-muted);font-weight:600;">${r.id}</td>
                        <td><strong>${r.vehicle_brand || 'Vehicle'} ${r.vehicle_model || ''}</strong> <small style="color:var(--text-muted);">(${r.vehicle_type || 'car'})</small></td>
                        <td style="max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${(r.symptoms || '').replace(/"/g, '&quot;')}">${r.symptoms || '—'}</td>
                        <td><span class="mono" style="color:var(--text-primary);font-weight:500;">${r.predicted_category || 'General'}</span></td>
                        <td class="mono" style="color:var(--text-secondary);font-variant-numeric:tabular-nums;font-weight:500;">${predictedDisplay}</td>
                        <td class="mono" style="color:var(--success);font-variant-numeric:tabular-nums;font-weight:600;">${actualDisplay}</td>
                        <td><span class="badge badge-${r.urgency || 'Medium'}" style="margin:0;padding:0.15rem 0.5rem;font-size:0.75rem;">${r.urgency || 'Medium'}</span></td>
                        <td style="color:var(--text-muted);font-size:0.81rem;">${r.timestamp ? r.timestamp.split(' ')[0] : 'Today'}</td>
                    </tr>
                `;}).join('');

                // Update pagination controls
                if (paginationContainer) {
                    paginationContainer.style.display = 'flex';
                    const pageInfo = document.getElementById('historyPageInfo');
                    const curNum = document.getElementById('currentPageNumber');
                    const firstBtn = document.getElementById('firstPageBtn');
                    const prevBtn = document.getElementById('prevPageBtn');
                    const nextBtn = document.getElementById('nextPageBtn');
                    const lastBtn = document.getElementById('lastPageBtn');

                    if (pageInfo) pageInfo.textContent = `Showing page ${currentHistoryPage} of ${totalHistoryPages} (${total} total records)`;
                    if (curNum) curNum.textContent = currentHistoryPage;
                    if (firstBtn) firstBtn.disabled = (currentHistoryPage <= 1);
                    if (prevBtn) prevBtn.disabled = (currentHistoryPage <= 1);
                    if (nextBtn) nextBtn.disabled = (currentHistoryPage >= totalHistoryPages);
                    if (lastBtn) lastBtn.disabled = (currentHistoryPage >= totalHistoryPages);
                }

                if (typeof lucide !== 'undefined' && lucide.createIcons) {
                    lucide.createIcons();
                }
            })
            .catch(() => {
                tbody.innerHTML = '<tr><td colspan="7" style="color:var(--danger);text-align:center;padding:2rem;">Failed to load service records.</td></tr>';
            });
    }

    const historyPageSizeSelect = document.getElementById('historyPageSizeSelect');
    if (historyPageSizeSelect) {
        historyPageSizeSelect.addEventListener('change', (e) => {
            historyPerPage = parseInt(e.target.value) || 20;
            loadHistoryRecords(1);
        });
    }

    const historySortSelect = document.getElementById('historySortSelect');
    if (historySortSelect) {
        historySortSelect.addEventListener('change', (e) => {
            currentHistorySort = e.target.value;
            loadHistoryRecords(1);
        });
    }

    document.getElementById('refreshHistoryBtn').addEventListener('click', () => loadHistoryRecords(currentHistoryPage));

    const firstPageBtn = document.getElementById('firstPageBtn');
    if (firstPageBtn) firstPageBtn.addEventListener('click', () => {
        if (currentHistoryPage > 1) loadHistoryRecords(1);
    });

    const prevPageBtn = document.getElementById('prevPageBtn');
    if (prevPageBtn) prevPageBtn.addEventListener('click', () => {
        if (currentHistoryPage > 1) loadHistoryRecords(currentHistoryPage - 1);
    });

    const nextPageBtn = document.getElementById('nextPageBtn');
    if (nextPageBtn) nextPageBtn.addEventListener('click', () => {
        if (currentHistoryPage < totalHistoryPages) loadHistoryRecords(currentHistoryPage + 1);
    });

    const lastPageBtn = document.getElementById('lastPageBtn');
    if (lastPageBtn) lastPageBtn.addEventListener('click', () => {
        if (currentHistoryPage < totalHistoryPages) loadHistoryRecords(totalHistoryPages);
    });

    // Workshop Analytics Loader (Chart.js)
    function loadAnalytics() {
        fetch('/api/analytics')
            .then(res => res.json())
            .then(data => {
                document.getElementById('statTotalDiagnoses').textContent = data.total_diagnoses || 0;
                document.getElementById('statAvgCost').textContent = `₹${(data.avg_estimated_cost || 0).toLocaleString('en-IN')}`;
                document.getElementById('statAvgRating').textContent = `${(data.feedback_stats?.avg_rating || 0).toFixed(1)} / 5 (${data.feedback_stats?.total_reviews || 0} reviews)`;

                renderCharts(data);
            });
    }

    function renderCharts(data) {
        if (typeof Chart === 'undefined') return;

        // Problem Categories Doughnut Chart
        const catCanvas = document.getElementById('chartCategory');
        if (catCanvas) {
            const catCtx = catCanvas.getContext('2d');
            const catLabels = Object.keys(data.category_distribution || {});
            const catValues = Object.values(data.category_distribution || {});

            if (categoryChart) categoryChart.destroy();
            categoryChart = new Chart(catCtx, {
                type: 'doughnut',
                data: {
                    labels: catLabels.length ? catLabels : ['No Data'],
                    datasets: [{
                        data: catValues.length ? catValues : [1],
                        backgroundColor: ['#5e6ad2', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6', '#64748b']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', boxWidth: 12 } } }
                }
            });
        }

        // Urgency Breakdown Bar Chart
        const urgCanvas = document.getElementById('chartUrgency');
        if (urgCanvas) {
            const urgCtx = urgCanvas.getContext('2d');
            const urgLabels = Object.keys(data.urgency_distribution || {});
            const urgValues = Object.values(data.urgency_distribution || {});

            if (urgencyChart) urgencyChart.destroy();
            urgencyChart = new Chart(urgCtx, {
                type: 'bar',
                data: {
                    labels: urgLabels.length ? urgLabels : ['Low', 'Medium', 'High'],
                    datasets: [{
                        label: 'Cases',
                        data: urgValues.length ? urgValues : [0, 0, 0],
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { ticks: { color: '#9ca3af', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                        x: { ticks: { color: '#9ca3af' }, grid: { display: false } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }
    }

    // Model Metrics Loader
    function loadMetrics() {
        fetch('/api/model/metrics')
            .then(res => res.json())
            .then(data => {
                if (data.classifier) {
                    document.getElementById('metricClassifierAcc').textContent = `${(data.classifier.accuracy * 100).toFixed(1)}%`;
                    document.getElementById('metricClassifierF1').textContent = data.classifier.f1_weighted;
                    const badgesContainer = document.getElementById('metricCategoriesBadges');
                    if (badgesContainer && data.classifier.categories) {
                        badgesContainer.innerHTML = data.classifier.categories.map(c => `
                            <span class="mono" style="font-size:0.75rem;background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.25);color:var(--accent);padding:0.2rem 0.5rem;border-radius:4px;">${c}</span>
                        `).join('');
                    }
                }
                if (data.regressor) {
                    document.getElementById('metricRegressorMae').textContent = `₹${Math.round(data.regressor.mae).toLocaleString('en-IN')}`;
                    document.getElementById('metricRegressorR2').textContent = data.regressor.r2_score;
                }
                document.getElementById('metricSamples').textContent = `${data.training_samples || 0} records`;
                document.getElementById('metricTrainedAt').textContent = data.trained_at ? data.trained_at.split('T')[0] : '—';

                if (typeof lucide !== 'undefined' && lucide.createIcons) {
                    lucide.createIcons();
                }
            })
            .catch(() => {});
    }

    // Quick Estimator Calculation
    function updateEstimatorResult() {
        const type = document.getElementById('est_type').value;
        const system = document.getElementById('est_system').value;
        const systemLabel = document.getElementById('estSystemLabel');
        const costValue = document.getElementById('estCostValue');
        const partsSplit = document.getElementById('estPartsSplit');
        const laborSplit = document.getElementById('estLaborSplit');

        if (baselineCosts[type] && baselineCosts[type][system]) {
            const [min, max] = baselineCosts[type][system];
            if (systemLabel) systemLabel.textContent = `${system} (${type})`;
            if (costValue) costValue.textContent = `₹${min.toLocaleString('en-IN')} – ₹${max.toLocaleString('en-IN')}`;

            // Benchmark ratios
            if (type === 'cycle') {
                if (partsSplit) partsSplit.textContent = '~50% Parts';
                if (laborSplit) laborSplit.textContent = '~50% Labor';
            } else if (system === 'Engine' || system === 'Transmission') {
                if (partsSplit) partsSplit.textContent = '~70% Parts';
                if (laborSplit) laborSplit.textContent = '~30% Labor';
            } else if (system === 'General Maintenance') {
                if (partsSplit) partsSplit.textContent = '~45% Consumables';
                if (laborSplit) laborSplit.textContent = '~55% Labor';
            } else {
                if (partsSplit) partsSplit.textContent = '~60% Parts';
                if (laborSplit) laborSplit.textContent = '~40% Labor';
            }
        }
    }

    document.getElementById('estBtn').addEventListener('click', updateEstimatorResult);
    document.getElementById('est_type').addEventListener('change', updateEstimatorResult);
    document.getElementById('est_system').addEventListener('change', updateEstimatorResult);

    // Auth & Role Modal Logic
    let isSignupMode = false;
    const authModal = document.getElementById('authModal');
    const authModalBtn = document.getElementById('authModalBtn');
    const closeAuthModal = document.getElementById('closeAuthModal');
    const authToggleLogin = document.getElementById('authToggleLogin');
    const authToggleSignup = document.getElementById('authToggleSignup');
    const authRoleGroup = document.getElementById('authRoleGroup');
    const authModalTitle = document.getElementById('authModalTitle');
    const authSubmitBtn = document.getElementById('authSubmitBtn');
    const authForm = document.getElementById('authForm');
    const authError = document.getElementById('authError');
    const logoutBtn = document.getElementById('logoutBtn');
    const roleBadge = document.getElementById('roleBadge');

    authModalBtn.addEventListener('click', () => {
        authModal.style.display = 'flex';
    });

    closeAuthModal.addEventListener('click', () => {
        authModal.style.display = 'none';
        authError.style.display = 'none';
    });

    authToggleLogin.addEventListener('click', () => {
        isSignupMode = false;
        authToggleLogin.className = 'btn-primary';
        authToggleSignup.className = 'btn-secondary';
        authRoleGroup.style.display = 'none';
        authModalTitle.textContent = 'Account Sign In';
        authSubmitBtn.textContent = 'Sign In';
        authError.style.display = 'none';
    });

    authToggleSignup.addEventListener('click', () => {
        isSignupMode = true;
        authToggleSignup.className = 'btn-primary';
        authToggleLogin.className = 'btn-secondary';
        authRoleGroup.style.display = 'block';
        authModalTitle.textContent = 'Create New Account';
        authSubmitBtn.textContent = 'Register';
        authError.style.display = 'none';
    });

    // Toast Notification Helper
    let toastTimeout = null;
    function showAuthToast(title, message, type = 'success') {
        const toast = document.getElementById('authToast');
        const toastTitle = document.getElementById('toastTitle');
        const toastMsg = document.getElementById('toastMessage');
        const toastIcon = document.getElementById('toastIcon');

        if (!toast) return;

        toast.className = `toast-popup toast-${type}`;
        if (toastTitle) toastTitle.textContent = title;
        if (toastMsg) toastMsg.textContent = message;

        if (toastIcon) {
            const iconName = type === 'success' ? 'check-circle' : 'info';
            toastIcon.innerHTML = `<i data-lucide="${iconName}" style="width:20px;height:20px;"></i>`;
        }

        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }

        toast.classList.add('show');

        if (toastTimeout) clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }

    authForm.addEventListener('submit', (e) => {
        e.preventDefault();
        authError.style.display = 'none';

        const username = document.getElementById('authUsername').value.trim();
        const password = document.getElementById('authPassword').value;
        const role = document.getElementById('authRole').value;

        const endpoint = isSignupMode ? '/api/auth/signup' : '/api/auth/login';
        const payload = isSignupMode ? { username, password, role } : { username, password };

        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => {
            if (!res.ok) return res.json().then(err => { throw new Error(err.error || 'Auth failed'); });
            return res.json();
        })
        .then(data => {
            authModal.style.display = 'none';
            applyAuthUI(data.user);
            if (isSignupMode) {
                const roleLabel = data.user.role === 'store_owner' ? 'Workshop Owner' : 'Vehicle Owner';
                showAuthToast('Account Created!', `Welcome, ${data.user.username}! Registered as ${roleLabel}.`, 'success');
            } else {
                showAuthToast('Logged In Successfully', `Welcome back, ${data.user.username}!`, 'success');
            }
        })
        .catch(err => {
            authError.textContent = err.message;
            authError.style.display = 'block';
        });
    });

    logoutBtn.addEventListener('click', () => {
        fetch('/api/auth/logout', { method: 'POST' })
            .then(() => {
                applyAuthUI(null);
                showAuthToast('Logged Out', 'You have been logged out of your account.', 'info');
            });
    });

    function checkAuthSession() {
        fetch('/api/auth/me')
            .then(res => res.json())
            .then(data => {
                applyAuthUI(data.user);
            })
            .catch(() => {
                applyAuthUI(null);
            });
    }

    function applyAuthUI(user) {
        currentUser = user;
        const recordsTitle = document.getElementById('recordsTableTitle');
        const recordsSubtitle = document.getElementById('recordsSubtitle');
        const historyTabLabel = document.getElementById('historyTabLabel');
        const ownerTabs = document.querySelectorAll('.owner-only-tab');

        if (user) {
            authModalBtn.style.display = 'none';
            logoutBtn.style.display = 'inline-flex';
            roleBadge.style.display = 'inline-block';
            const displayRole = user.role === 'store_owner' ? 'Workshop Owner' : 'Vehicle Owner';
            roleBadge.textContent = `${user.username} (${displayRole})`;

            if (user.role === 'store_owner') {
                // Show Owner analytics & telemetry tabs
                ownerTabs.forEach(tab => tab.style.display = 'inline-flex');
                if (historyTabLabel) historyTabLabel.textContent = 'All Workshop Records';
                if (recordsTitle) recordsTitle.textContent = 'Workshop Customer Repair Logs';
                if (recordsSubtitle) recordsSubtitle.textContent = 'Complete customer diagnostic logs & history';
            } else {
                // Customer role: hide Workshop analytics tabs
                ownerTabs.forEach(tab => tab.style.display = 'none');
                if (historyTabLabel) historyTabLabel.textContent = 'My Service History';
                if (recordsTitle) recordsTitle.textContent = 'My Vehicle Service History';
                if (recordsSubtitle) recordsSubtitle.textContent = 'Diagnostic reports created by your account';

                // If user was on an owner-only tab, switch back to diagnostic assistant
                const activeTab = document.querySelector('.tab-btn.active');
                if (activeTab && (activeTab.id === 'btn-analytics' || activeTab.id === 'btn-metrics')) {
                    switchTab('assess');
                }
            }
        } else {
            // Guest mode
            authModalBtn.style.display = 'inline-flex';
            logoutBtn.style.display = 'none';
            roleBadge.style.display = 'none';
            ownerTabs.forEach(tab => tab.style.display = 'none');
            if (historyTabLabel) historyTabLabel.textContent = 'Service Records';
            if (recordsTitle) recordsTitle.textContent = 'Recent Service Records';
            if (recordsSubtitle) recordsSubtitle.textContent = 'Showing public diagnostic history';

            const activeTab = document.querySelector('.tab-btn.active');
            if (activeTab && (activeTab.id === 'btn-analytics' || activeTab.id === 'btn-metrics')) {
                switchTab('assess');
            }
        }
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }

    // Initialize Lucide icons on DOM ready
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
    }
});
