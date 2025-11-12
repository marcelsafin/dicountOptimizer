// Shopping Optimizer - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('optimizer-form');
    const optimizeBtn = document.getElementById('optimize-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsSection = document.getElementById('results-section');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');

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
        const preferences = document.querySelectorAll('input[name="preferences"]:checked');

        if (!location) {
            showError('Please enter a location');
            return false;
        }

        if (!mealPlan) {
            showError('Please enter at least one meal in your meal plan');
            return false;
        }

        if (preferences.length === 0) {
            showError('Please select at least one optimization preference');
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
        const preferences = Array.from(document.querySelectorAll('input[name="preferences"]:checked'))
            .map(cb => cb.value);

        // Parse meal plan into array
        const meals = mealPlan.split('\n')
            .map(meal => meal.trim())
            .filter(meal => meal.length > 0);

        return {
            location: location,
            meals: meals,
            preferences: {
                maximize_savings: preferences.includes('cost'),
                minimize_stores: preferences.includes('time'),
                prefer_organic: preferences.includes('quality')
            }
        };
    }

    /**
     * Optimize shopping plan (placeholder - will be implemented in task 10)
     */
    function optimizeShoppingPlan(formData) {
        // Placeholder: Simulate API call with timeout
        setTimeout(() => {
            // This will be replaced with actual ADK agent call in task 10
            displayPlaceholderResults();
        }, 1500);
    }

    /**
     * Display placeholder results (for UI testing)
     */
    function displayPlaceholderResults() {
        hideLoading();
        
        // Populate shopping list
        const shoppingList = document.getElementById('shopping-list');
        shoppingList.innerHTML = `
            <p><em>Shopping recommendations will appear here after optimization...</em></p>
            <p style="margin-top: 10px; color: #666;">
                This section will show which products to buy at which stores, organized by day.
            </p>
        `;

        // Populate savings
        document.getElementById('monetary-savings').textContent = 'DKK 0.00';
        document.getElementById('time-savings').textContent = '0 hours';

        // Populate tips
        const tipsList = document.getElementById('tips-list');
        tipsList.innerHTML = `
            <li>Tips and recommendations will appear here...</li>
            <li>Time-sensitive discount opportunities will be highlighted</li>
            <li>Organic product recommendations will be shown</li>
        `;

        // Populate motivation message
        const motivationMessage = document.getElementById('motivation-message');
        motivationMessage.textContent = 'Your personalized shopping plan will include a motivational message here!';

        // Show results section
        resultsSection.style.display = 'block';
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
