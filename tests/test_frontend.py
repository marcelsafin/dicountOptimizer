"""
Frontend and UI validation tests for Shopping Optimizer.

Tests HTML structure, CSS styling, JavaScript validation, and UI components.
"""

import sys
import os
from pathlib import Path


def test_html_structure():
    """Test that HTML file exists and has required structure."""
    print("\n=== Test 1: HTML Structure Validation ===")
    
    html_path = Path("templates/index.html")
    assert html_path.exists(), "index.html not found"
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check required HTML elements (using flexible matching for multi-line elements)
    required_ids = [
        'id="optimizer-form"',
        'id="location"',
        'id="meal-plan"',
        'id="pref-cost"',
        'id="pref-time"',
        'id="pref-quality"',
        'id="get-location-btn"',
        'id="results-section"',
        'id="loading-spinner"',
        'id="error-message"',
    ]
    
    for element_id in required_ids:
        assert element_id in html_content, f"Missing required element: {element_id}"
    
    # Check input types
    assert 'type="text"' in html_content, "Missing text input"
    assert 'type="range"' in html_content, "Missing range inputs (sliders)"
    assert 'type="submit"' in html_content, "Missing submit button"
    assert 'type="button"' in html_content, "Missing button elements"
    
    # Check slider attributes
    assert 'min="0"' in html_content, "Sliders missing min attribute"
    assert 'max="5"' in html_content, "Sliders missing max attribute"
    assert 'value="0"' in html_content, "Sliders missing default value"
    
    # Check required attributes
    assert 'required' in html_content, "Missing required attributes on inputs"
    
    print("✓ HTML structure is valid")
    print(f"  - All required form elements present")
    print(f"  - Sliders configured with min=0, max=5")
    print(f"  - Required attributes set")


def test_css_styling():
    """Test that CSS file exists and has required styles."""
    print("\n=== Test 2: CSS Styling Validation ===")
    
    css_path = Path("static/css/styles.css")
    assert css_path.exists(), "styles.css not found"
    
    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    # Check required CSS classes
    required_classes = [
        '.container',
        '.form-group',
        '.slider-group',
        '.slider-item',
        '.slider-header',
        '.slider-label',
        '.slider-value',
        '.slider',
        '.btn-optimize',
        '.btn-location',
        '.location-input-group',
        '.loading-spinner',
        '.error-message',
        '.results-section',
    ]
    
    for css_class in required_classes:
        assert css_class in css_content, f"Missing CSS class: {css_class}"
    
    # Check slider styling specifics
    assert '.slider::-webkit-slider-thumb' in css_content, "Missing webkit slider thumb styles"
    assert '.slider::-moz-range-thumb' in css_content, "Missing firefox slider thumb styles"
    assert 'margin-top: -8px' in css_content, "Slider thumb not vertically centered"
    assert 'cubic-bezier' in css_content, "Missing smooth transitions"
    
    # Check responsive design
    assert '@media' in css_content, "Missing responsive design media queries"
    
    print("✓ CSS styling is valid")
    print(f"  - All required classes present")
    print(f"  - Slider thumbs vertically centered")
    print(f"  - Smooth transitions implemented")
    print(f"  - Responsive design included")


def test_javascript_validation():
    """Test that JavaScript file exists and has required functions."""
    print("\n=== Test 3: JavaScript Validation Logic ===")
    
    js_path = Path("static/js/app.js")
    assert js_path.exists(), "app.js not found"
    
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    # Check required functions
    required_functions = [
        'validateForm',
        'getFormData',
        'optimizeShoppingPlan',
        'displayResults',
        'showLoading',
        'hideLoading',
        'showError',
        'hideError',
    ]
    
    for func in required_functions:
        assert f'function {func}' in js_content or f'{func}(' in js_content, \
            f"Missing required function: {func}"
    
    # Check slider event listeners
    assert 'costSlider.addEventListener' in js_content, "Missing cost slider event listener"
    assert 'timeSlider.addEventListener' in js_content, "Missing time slider event listener"
    assert 'qualitySlider.addEventListener' in js_content, "Missing quality slider event listener"
    
    # Check validation logic
    assert 'if (!location)' in js_content, "Missing location validation"
    assert 'if (!mealPlan)' in js_content, "Missing meal plan validation"
    assert 'costValue === 0 && timeValue === 0 && qualityValue === 0' in js_content, \
        "Missing slider validation (at least one must be > 0)"
    
    # Check geolocation
    assert 'navigator.geolocation' in js_content, "Missing geolocation functionality"
    assert 'getCurrentPosition' in js_content, "Missing getCurrentPosition call"
    
    # Check API call
    assert "fetch('/api/optimize'" in js_content, "Missing API fetch call"
    assert 'method: \'POST\'' in js_content, "Missing POST method"
    
    # Check event listeners
    assert 'addEventListener' in js_content, "Missing event listeners"
    assert 'DOMContentLoaded' in js_content, "Missing DOMContentLoaded event"
    
    print("✓ JavaScript validation is valid")
    print(f"  - All required functions present")
    print(f"  - Form validation implemented")
    print(f"  - Geolocation functionality included")
    print(f"  - API integration configured")


def test_ui_components():
    """Test that all UI components are properly configured."""
    print("\n=== Test 4: UI Components Validation ===")
    
    html_path = Path("templates/index.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Test slider configuration
    slider_count = html_content.count('<input type="range"')
    assert slider_count == 3, f"Expected 3 sliders, found {slider_count}"
    
    # Test slider value displays
    value_display_count = html_content.count('class="slider-value"')
    assert value_display_count == 3, f"Expected 3 value displays, found {value_display_count}"
    
    # Test form structure
    assert '<form id="optimizer-form">' in html_content, "Form not properly structured"
    assert 'type="submit"' in html_content, "Missing submit button"
    
    # Test accessibility
    assert 'title=' in html_content, "Missing accessibility titles"
    assert 'placeholder=' in html_content, "Missing input placeholders"
    
    # Test results section
    assert 'id="shopping-list"' in html_content, "Missing shopping list container"
    assert 'id="monetary-savings"' in html_content, "Missing monetary savings display"
    assert 'id="time-savings"' in html_content, "Missing time savings display"
    assert 'id="tips-list"' in html_content, "Missing tips list"
    assert 'id="motivation-message"' in html_content, "Missing motivation message"
    
    print("✓ UI components are valid")
    print(f"  - 3 sliders configured (Cost, Time, Quality)")
    print(f"  - 3 value displays present")
    print(f"  - Form structure correct")
    print(f"  - Accessibility features included")
    print(f"  - Results section complete")


def test_file_structure():
    """Test that all required files exist in correct locations."""
    print("\n=== Test 5: File Structure Validation ===")
    
    required_files = [
        "templates/index.html",
        "static/css/styles.css",
        "static/js/app.js",
        "app.py",
    ]
    
    for file_path in required_files:
        path = Path(file_path)
        assert path.exists(), f"Required file not found: {file_path}"
        assert path.stat().st_size > 0, f"File is empty: {file_path}"
    
    print("✓ File structure is valid")
    print(f"  - All required files present")
    print(f"  - No empty files")


def test_slider_range_validation():
    """Test that sliders have correct range and step configuration."""
    print("\n=== Test 6: Slider Range Validation ===")
    
    html_path = Path("templates/index.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract slider configurations
    import re
    sliders = re.findall(r'<input type="range"[^>]*>', html_content)
    
    assert len(sliders) == 3, f"Expected 3 sliders, found {len(sliders)}"
    
    for slider in sliders:
        assert 'min="0"' in slider, f"Slider missing min=0: {slider}"
        assert 'max="5"' in slider, f"Slider missing max=5: {slider}"
        assert 'value="0"' in slider, f"Slider missing default value=0: {slider}"
        assert 'class="slider"' in slider, f"Slider missing class: {slider}"
    
    print("✓ Slider range validation passed")
    print(f"  - All sliders: min=0, max=5, default=0")
    print(f"  - Proper CSS classes applied")


def test_error_handling():
    """Test that error handling UI elements are present."""
    print("\n=== Test 7: Error Handling UI Validation ===")
    
    html_path = Path("templates/index.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    js_path = Path("static/js/app.js")
    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    # Check HTML error elements
    assert 'id="error-message"' in html_content, "Missing error message container"
    assert 'id="error-text"' in html_content, "Missing error text element"
    
    # Check JavaScript error handling
    assert 'showError' in js_content, "Missing showError function"
    assert 'hideError' in js_content, "Missing hideError function"
    assert 'try {' in js_content and 'catch' in js_content, "Missing try-catch blocks"
    
    # Check error messages
    error_messages = [
        'Please enter a location',
        'Please enter at least one meal',
        'Please set at least one optimization preference above 0',
    ]
    
    for msg in error_messages:
        assert msg in js_content, f"Missing error message: {msg}"
    
    print("✓ Error handling UI is valid")
    print(f"  - Error display elements present")
    print(f"  - Error handling functions implemented")
    print(f"  - User-friendly error messages defined")


def test_slider_smooth_interaction():
    """Test that sliders have smooth transitions and proper interaction styles."""
    print("\n=== Test 8: Slider Smooth Interaction Validation ===")
    
    css_path = Path("static/css/styles.css")
    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    # Check for smooth transitions using cubic-bezier
    assert 'cubic-bezier' in css_content, "Missing cubic-bezier for smooth transitions"
    assert 'transition:' in css_content or 'transition ' in css_content, \
        "Missing CSS transitions for smooth animation"
    
    # Check webkit slider thumb has transition
    webkit_thumb_section = css_content[css_content.find('.slider::-webkit-slider-thumb'):
                                       css_content.find('.slider::-webkit-slider-thumb:hover')]
    assert 'transition' in webkit_thumb_section, \
        "Webkit slider thumb missing transition property"
    
    # Check firefox slider thumb has transition
    moz_thumb_section = css_content[css_content.find('.slider::-moz-range-thumb'):
                                    css_content.find('.slider::-moz-range-thumb:hover')]
    assert 'transition' in moz_thumb_section, \
        "Firefox slider thumb missing transition property"
    
    # Check for hover effects (smooth scaling)
    assert 'transform: scale' in css_content, "Missing smooth scale transform on hover"
    assert ':hover' in css_content, "Missing hover states for interactive feedback"
    
    # Check for active/grabbing state
    assert 'cursor: grab' in css_content, "Missing grab cursor for better UX"
    assert 'cursor: grabbing' in css_content or ':active' in css_content, \
        "Missing active/grabbing state for slider interaction"
    
    # Check thumb is vertically centered
    assert 'margin-top: -8px' in css_content or 'margin-top:-8px' in css_content, \
        "Slider thumb not vertically centered (missing margin-top adjustment)"
    
    # Check for smooth value display animation
    slider_value_section = css_content[css_content.find('.slider-value'):
                                       css_content.find('.slider-value') + 300]
    assert 'transition' in slider_value_section, \
        "Slider value display missing smooth transition"
    
    # Verify transition timing is reasonable (not too slow, not instant)
    import re
    transitions = re.findall(r'transition:[^;]+;', css_content)
    has_reasonable_timing = any('0.1s' in t or '0.2s' in t or '0.15s' in t for t in transitions)
    assert has_reasonable_timing, \
        "Transitions should use reasonable timing (0.1s-0.2s) for smooth feel"
    
    print("✓ Slider smooth interaction is valid")
    print(f"  - Cubic-bezier easing functions present")
    print(f"  - Smooth transitions on thumb (webkit & firefox)")
    print(f"  - Hover and active states implemented")
    print(f"  - Grab/grabbing cursors for better UX")
    print(f"  - Thumb vertically centered on track")
    print(f"  - Value display has smooth animation")
    print(f"  - Reasonable transition timing (0.1-0.2s)")


def run_all_tests():
    """Run all frontend validation tests."""
    print("=" * 70)
    print("SHOPPING OPTIMIZER - FRONTEND & UI VALIDATION TESTS")
    print("=" * 70)
    
    tests = [
        test_html_structure,
        test_css_styling,
        test_javascript_validation,
        test_ui_components,
        test_file_structure,
        test_slider_range_validation,
        test_error_handling,
        test_slider_smooth_interaction,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 All frontend validation tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
