// Shopping Optimizer - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('optimizer-form');
    const optimizeBtn = document.getElementById('optimize-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsSection = document.getElementById('results-section');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const getLocationBtn = document.getElementById('get-location-btn');
    const locationInput = document.getElementById('location');
    
    // Slider elements
    const costSlider = document.getElementById('pref-cost');
    const timeSlider = document.getElementById('pref-time');
    const qualitySlider = document.getElementById('pref-quality');
    const costValue = document.getElementById('cost-value');
    const timeValue = document.getElementById('time-value');
    const qualityValue = document.getElementById('quality-value');

    // Update slider value displays with one decimal place
    costSlider.addEventListener('input', function() {
        costValue.textContent = parseFloat(this.value).toFixed(1);
    });
    
    timeSlider.addEventListener('input', function() {
        timeValue.textContent = parseFloat(this.value).toFixed(1);
    });
    
    qualitySlider.addEventListener('input', function() {
        qualityValue.textContent = parseFloat(this.value).toFixed(1);
    });

    // Geolocation button handler
    getLocationBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
            showError('Geolocation is not supported by your browser');
            return;
        }

        // Disable button and show loading state
        getLocationBtn.disabled = true;
        getLocationBtn.textContent = '⏳';

        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude.toFixed(4);
                const lon = position.coords.longitude.toFixed(4);
                locationInput.value = `${lat},${lon}`;
                
                // Reset button
                getLocationBtn.disabled = false;
                getLocationBtn.textContent = '📍';
            },
            function(error) {
                let errorMsg = 'Unable to get your location';
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Location permission denied. Please enable location access.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Location information unavailable';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Location request timed out';
                        break;
                }
                showError(errorMsg);
                
                // Reset button
                getLocationBtn.disabled = false;
                getLocationBtn.textContent = '📍';
            }
        );
    });

    // Form submission handler
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Clear previous errors
        hideError();
        
        // Validate form
        if (!validateForm()) {
            return;
        }
        
        // Get form data
        const formData = getFormData();
        
        // Show loading state
        showLoading();
        
        // Call optimization function (placeholder for now)
        optimizeShoppingPlan(formData);
    });

    /**
     * Validate form inputs
     */
    function validateForm() {
        const location = document.getElementById('location').value.trim();
        const mealPlan = document.getElementById('meal-plan').value.trim();
        const costValue = parseFloat(costSlider.value);
        const timeValue = parseFloat(timeSlider.value);
        const qualityValue = parseFloat(qualitySlider.value);

        if (!location) {
            showError('Please enter a location');
            return false;
        }

        // Meal plan is now optional - AI will suggest if empty
        // No validation needed for meal plan

        if (costValue === 0 && timeValue === 0 && qualityValue === 0) {
            showError('Please set at least one optimization preference above 0');
            return false;
        }

        return true;
    }

    /**
     * Get form data as an object
     */
    function getFormData() {
        const location = document.getElementById('location').value.trim();
        const mealPlan = document.getElementById('meal-plan').value.trim();
        const costValue = parseFloat(costSlider.value);
        const timeValue = parseFloat(timeSlider.value);
        const qualityValue = parseFloat(qualitySlider.value);

        // Parse meal plan into array (or send as single preference string)
        let meals = [];
        if (mealPlan) {
            // Check if it's a description or a list
            if (mealPlan.includes('\n')) {
                // Multiple lines - treat as meal list
                meals = mealPlan.split('\n')
                    .map(meal => meal.trim())
                    .filter(meal => meal.length > 0);
            } else {
                // Single line - could be preference or single meal
                meals = [mealPlan.trim()];
            }
        }
        // If empty, AI will suggest meals based on discounts

        return {
            location: location,
            meals: meals,
            preferences: {
                maximize_savings: costValue > 0,
                minimize_stores: timeValue > 0,
                prefer_organic: qualityValue > 0
            },
            preference_weights: {
                cost: costValue,
                time: timeValue,
                quality: qualityValue
            }
        };
    }

    /**
     * Optimize shopping plan by calling the backend API
     */
    async function optimizeShoppingPlan(formData) {
        try {
            const response = await fetch('/api/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                displayResults(result);
            } else {
                hideLoading();
                showError(result.error || 'Optimization failed. Please try again.');
            }
        } catch (error) {
            hideLoading();
            showError('Failed to connect to the server. Please try again.');
            console.error('Optimization error:', error);
        }
    }

    /**
     * Display optimization results
     */
    function displayResults(result) {
        hideLoading();
        
        // Parse the recommendation text to extract structured data
        const recommendation = result.recommendation;
        
        // Populate shopping list with formatted recommendation
        const shoppingList = document.getElementById('shopping-list');
        shoppingList.innerHTML = formatRecommendationHTML(recommendation);

        // Populate savings
        const totalSavings = result.total_savings || 0;
        const timeSavings = result.time_savings || 0;
        
        document.getElementById('monetary-savings').textContent = `${totalSavings.toFixed(2)} kr`;
        document.getElementById('time-savings').textContent = `${timeSavings.toFixed(2)} hours`;

        // Extract and populate tips from recommendation
        const tips = extractTips(recommendation);
        const tipsList = document.getElementById('tips-list');
        if (tips.length > 0) {
            tipsList.innerHTML = tips.map(tip => `<li>${escapeHtml(tip)}</li>`).join('');
        } else {
            tipsList.innerHTML = '<li>No specific tips available for this shopping plan.</li>';
        }

        // Extract and populate motivation message
        const motivation = extractMotivation(recommendation);
        const motivationMessage = document.getElementById('motivation-message');
        motivationMessage.textContent = motivation || 'Happy shopping! Your optimized plan is ready.';

        // Show results section
        resultsSection.style.display = 'block';
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Format recommendation text as HTML
     */
    function formatRecommendationHTML(recommendation) {
        if (!recommendation) {
            return '<p>No recommendations available.</p>';
        }

        // Split by lines and format
        const lines = recommendation.split('\n');
        let html = '';
        let inList = false;

        for (let line of lines) {
            line = line.trim();
            if (!line) continue;

            // Check if it's a store/day header (contains emoji or all caps)
            if (line.match(/^[🏪📅🛒]/) || line.match(/^[A-ZÆØÅ\s]+:/) || line.includes('**')) {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                // Remove markdown bold markers
                line = line.replace(/\*\*/g, '');
                html += `<h4 style="margin-top: 15px; margin-bottom: 8px; color: #667eea; font-size: 1.1rem;">${escapeHtml(line)}</h4>`;
            } else if (line.match(/^[-•*]\s/) || line.match(/^\d+\.\s/)) {
                // It's a list item
                if (!inList) {
                    html += '<ul style="list-style: none; padding-left: 0;">';
                    inList = true;
                }
                // Remove list markers
                line = line.replace(/^[-•*]\s/, '').replace(/^\d+\.\s/, '');
                html += `<li style="padding: 8px 0; padding-left: 20px; position: relative;">
                    <span style="position: absolute; left: 0; color: #667eea;">→</span>
                    ${escapeHtml(line)}
                </li>`;
            } else if (!line.includes('Tips:') && !line.includes('Motivation:')) {
                // Regular paragraph (skip tips and motivation sections as they're shown separately)
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                html += `<p style="margin: 8px 0;">${escapeHtml(line)}</p>`;
            }
        }

        if (inList) {
            html += '</ul>';
        }

        return html || '<p>No shopping list available.</p>';
    }

    /**
     * Extract tips from recommendation text
     */
    function extractTips(recommendation) {
        const tips = [];
        const lines = recommendation.split('\n');
        let inTipsSection = false;

        for (let line of lines) {
            line = line.trim();
            
            if (line.includes('Tips:') || line.includes('💡')) {
                inTipsSection = true;
                continue;
            }
            
            if (inTipsSection) {
                if (line.includes('Motivation:') || line.includes('🎉')) {
                    break;
                }
                if (line.match(/^[-•*]\s/) || line.match(/^\d+\.\s/)) {
                    const tip = line.replace(/^[-•*]\s/, '').replace(/^\d+\.\s/, '').trim();
                    if (tip) tips.push(tip);
                }
            }
        }

        return tips;
    }

    /**
     * Extract motivation message from recommendation text
     */
    function extractMotivation(recommendation) {
        const lines = recommendation.split('\n');
        let inMotivationSection = false;
        let motivation = '';

        for (let line of lines) {
            line = line.trim();
            
            if (line.includes('Motivation:') || line.includes('🎉')) {
                inMotivationSection = true;
                continue;
            }
            
            if (inMotivationSection && line) {
                motivation += line + ' ';
            }
        }

        return motivation.trim();
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show loading spinner
     */
    function showLoading() {
        optimizeBtn.disabled = true;
        loadingSpinner.style.display = 'block';
        resultsSection.style.display = 'none';
    }

    /**
     * Hide loading spinner
     */
    function hideLoading() {
        optimizeBtn.disabled = false;
        loadingSpinner.style.display = 'none';
    }

    /**
     * Show error message
     */
    function showError(message) {
        errorText.textContent = message;
        errorMessage.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            hideError();
        }, 5000);
    }

    /**
     * Hide error message
     */
    function hideError() {
        errorMessage.style.display = 'none';
    }
});
