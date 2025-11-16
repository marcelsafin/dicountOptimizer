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

        if (!mealPlan) {
            showError('Please enter at least one meal');
            return false;
        }

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

        // Get meal type filters
        const mealTypes = [];
        document.querySelectorAll('input[name="meal-type"]:checked').forEach(checkbox => {
            mealTypes.push(checkbox.value);
        });

        // Get excluded ingredients
        const excludeInput = document.getElementById('exclude-ingredients').value.trim();
        const excludedIngredients = excludeInput 
            ? excludeInput.split(',').map(item => item.trim()).filter(item => item.length > 0)
            : [];

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
            meal_types: mealTypes,
            excluded_ingredients: excludedIngredients,
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

            if (response.ok && result.success) {
                displayResults(result);
            } else {
                hideLoading();
                
                // Show specific error message based on error type
                let errorMessage = result.error || 'Optimization failed. Please try again.';
                
                if (result.error_type === 'validation') {
                    errorMessage = `Input validation error: ${result.error}`;
                } else if (result.error_type === 'optimization') {
                    errorMessage = `Optimization error: ${result.error}`;
                } else if (result.error_type === 'server') {
                    errorMessage = `Server error: ${result.error}`;
                }
                
                // Add correlation ID for debugging if available
                if (result.correlation_id) {
                    console.error('Error correlation ID:', result.correlation_id);
                    errorMessage += ` (ID: ${result.correlation_id.substring(0, 8)})`;
                }
                
                showError(errorMessage);
            }
        } catch (error) {
            hideLoading();
            showError('Failed to connect to the server. Please check your internet connection and try again.');
            console.error('Optimization error:', error);
        }
    }

    /**
     * Display optimization results
     */
    function displayResults(result) {
        hideLoading();
        
        // Extract recommendation data from new Pydantic model structure
        const recommendation = result.recommendation;
        
        // Display map with stores
        if (recommendation.stores && recommendation.stores.length > 0 && result.user_location) {
            displayStoreMap(recommendation.stores, result.user_location);
            displayStoreList(recommendation.stores);
        }
        
        // Populate shopping list with purchases
        const shoppingList = document.getElementById('shopping-list');
        shoppingList.innerHTML = formatPurchasesHTML(recommendation.purchases, recommendation.stores);

        // Populate savings
        const totalSavings = recommendation.total_savings || 0;
        const timeSavings = recommendation.time_savings || 0;
        
        document.getElementById('monetary-savings').textContent = `${parseFloat(totalSavings).toFixed(2)} kr`;
        document.getElementById('time-savings').textContent = `${parseFloat(timeSavings).toFixed(1)} minutes`;

        // Populate tips from recommendation
        const tipsList = document.getElementById('tips-list');
        if (recommendation.tips && recommendation.tips.length > 0) {
            tipsList.innerHTML = recommendation.tips.map(tip => `<li>${escapeHtml(tip)}</li>`).join('');
        } else {
            tipsList.innerHTML = '<li>No specific tips available for this shopping plan.</li>';
        }

        // Populate motivation message
        const motivationMessage = document.getElementById('motivation-message');
        motivationMessage.textContent = recommendation.motivation_message || 'Happy shopping! Your optimized plan is ready.';

        // Show results section
        resultsSection.style.display = 'block';
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Format purchases as HTML grouped by store and day
     */
    function formatPurchasesHTML(purchases, stores) {
        if (!purchases || purchases.length === 0) {
            return '<p>No purchases recommended. Try adjusting your preferences or location.</p>';
        }

        // Group purchases by store
        const purchasesByStore = {};
        purchases.forEach(purchase => {
            if (!purchasesByStore[purchase.store_name]) {
                purchasesByStore[purchase.store_name] = [];
            }
            purchasesByStore[purchase.store_name].push(purchase);
        });

        let html = '';
        
        // Display purchases grouped by store
        Object.entries(purchasesByStore).forEach(([storeName, storePurchases], storeIndex) => {
            // Find store details
            const storeInfo = stores.find(s => s.name === storeName);
            const storeNumber = storeIndex + 1;
            
            html += `<div class="store-section" style="margin-bottom: 25px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">`;
            html += `<h4 style="margin: 0 0 12px 0; color: #667eea; display: flex; align-items: center; gap: 8px;">`;
            html += `<span style="background: #667eea; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">${storeNumber}</span>`;
            html += `${escapeHtml(storeName)}`;
            if (storeInfo && storeInfo.distance_km) {
                html += ` <span style="font-size: 0.85rem; color: #666; font-weight: normal;">(${storeInfo.distance_km.toFixed(1)} km)</span>`;
            }
            html += `</h4>`;
            
            html += '<ul style="list-style: none; padding-left: 0; margin: 0;">';
            
            storePurchases.forEach(purchase => {
                const savings = parseFloat(purchase.savings);
                const price = parseFloat(purchase.price);
                const savingsPercent = savings > 0 && price > 0 ? ((savings / (price + savings)) * 100).toFixed(0) : 0;
                
                html += `<li style="padding: 10px 0; border-bottom: 1px solid #e0e0e0; display: flex; justify-content: space-between; align-items: start;">`;
                html += `<div style="flex: 1;">`;
                html += `<div style="font-weight: 500; color: #333;">${escapeHtml(purchase.product_name)}</div>`;
                html += `<div style="font-size: 0.85rem; color: #666; margin-top: 4px;">`;
                html += `For: ${escapeHtml(purchase.meal_association)} • `;
                html += `Buy on: ${formatDate(purchase.purchase_day)}`;
                html += `</div>`;
                html += `</div>`;
                html += `<div style="text-align: right; margin-left: 15px;">`;
                html += `<div style="font-weight: 600; color: #667eea;">${price.toFixed(2)} kr</div>`;
                if (savings > 0) {
                    html += `<div style="font-size: 0.85rem; color: #10b981;">Save ${savings.toFixed(2)} kr (${savingsPercent}%)</div>`;
                }
                html += `</div>`;
                html += `</li>`;
            });
            
            html += '</ul>';
            html += '</div>';
        });

        return html;
    }
    
    /**
     * Format date for display
     */
    function formatDate(dateString) {
        const date = new Date(dateString);
        const options = { weekday: 'short', month: 'short', day: 'numeric' };
        return date.toLocaleDateString('en-US', options);
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
        
        // Scroll to error message
        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Auto-hide after 8 seconds (longer for users to read)
        setTimeout(() => {
            hideError();
        }, 8000);
    }

    /**
     * Hide error message
     */
    function hideError() {
        errorMessage.style.display = 'none';
    }

    /**
     * Display store map using Leaflet
     */
    let storeMapInstance = null;
    
    function displayStoreMap(stores, userLocation) {
        const mapContainer = document.getElementById('store-map');
        
        // Clear existing map if any
        if (storeMapInstance) {
            storeMapInstance.remove();
        }
        
        // Validate user location
        if (!userLocation || !userLocation.latitude || !userLocation.longitude) {
            console.warn('Invalid user location for map display');
            return;
        }
        
        // Create map centered on user location
        storeMapInstance = L.map('store-map').setView(
            [userLocation.latitude, userLocation.longitude], 
            13
        );
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(storeMapInstance);
        
        // Add user location marker
        const userIcon = L.divIcon({
            className: 'user-marker',
            html: '<div style="background: #667eea; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        L.marker([userLocation.latitude, userLocation.longitude], { icon: userIcon })
            .addTo(storeMapInstance)
            .bindPopup('<strong>Your Location</strong>');
        
        // Add store markers (if stores have location data)
        const storesWithLocation = stores.filter(s => s.latitude && s.longitude);
        
        storesWithLocation.forEach((store, index) => {
            const storeIcon = L.divIcon({
                className: 'store-marker',
                html: `<div style="background: #ff6b6b; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px;">${index + 1}</div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            
            const itemsText = store.items === 1 ? '1 item' : `${store.items} items`;
            
            L.marker([store.latitude, store.longitude], { icon: storeIcon })
                .addTo(storeMapInstance)
                .bindPopup(`
                    <strong>${escapeHtml(store.name)}</strong><br>
                    <small>${escapeHtml(store.address || 'Address not available')}</small><br>
                    <small style="color: #667eea; font-weight: 600;">${(store.distance_km || 0).toFixed(1)} km away</small><br>
                    <small>${itemsText} to purchase</small>
                `);
        });
        
        // Fit map to show all markers
        if (storesWithLocation.length > 0) {
            const bounds = L.latLngBounds([
                [userLocation.latitude, userLocation.longitude],
                ...storesWithLocation.map(s => [s.latitude, s.longitude])
            ]);
            storeMapInstance.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    /**
     * Display store list below map
     */
    function displayStoreList(stores) {
        const storeList = document.getElementById('store-list');
        
        if (!stores || stores.length === 0) {
            storeList.innerHTML = '<p style="text-align: center; color: #666;">No stores found.</p>';
            return;
        }
        
        const storeCards = stores.map((store, index) => {
            const itemCount = store.items || 0;
            const itemText = itemCount === 1 ? '1 item' : `${itemCount} items`;
            const distanceKm = store.distance_km || 0;
            const address = store.address || 'Address not available';
            
            return `
                <div class="store-card">
                    <div class="store-card-header">
                        <span style="background: #ff6b6b; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">${index + 1}</span>
                        <h4>${escapeHtml(store.name)}</h4>
                    </div>
                    <div class="store-card-address">${escapeHtml(address)}</div>
                    <div class="store-card-distance">📍 ${distanceKm.toFixed(1)} km away</div>
                    <div class="store-card-products">
                        <strong>${itemText}</strong> to purchase
                    </div>
                </div>
            `;
        }).join('');
        
        storeList.innerHTML = storeCards;
    }

    /**
     * Helper function to display product with image if available
     * Note: Currently Salling API doesn't provide image URLs, but this is ready for future use
     */
    function formatProductWithImage(product) {
        if (product.image_url) {
            return `
                <div class="product-with-image">
                    <img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}" class="product-image" />
                    <div class="product-details">
                        <strong>${escapeHtml(product.name)}</strong><br>
                        <small>${product.price} kr (${product.discount_percent}% off)</small>
                    </div>
                </div>
            `;
        } else {
            return `<div>${escapeHtml(product.name)} - ${product.price} kr (${product.discount_percent}% off)</div>`;
        }
    }
});
