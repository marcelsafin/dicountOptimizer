# Troubleshooting Guide

## Common Issues

### "No food waste products found"

**Possible Causes**:
- Location is outside Denmark (Salling API only covers Danish stores)
- No stores within 2km radius
- No food waste available at nearby stores today

**Solutions**:
- Try a different location in Denmark (e.g., Copenhagen, Aarhus, Odense)
- Check that coordinates are correct (latitude, longitude)
- Try again later - food waste inventory changes throughout the day

### "API Error: 401 Unauthorized"

**Cause**: Invalid or missing Salling Group API key

**Solutions**:
1. Verify your API key is correct in `.env` file
2. Check that you copied the entire key (no extra spaces)
3. Ensure your Salling Group account is active
4. Generate a new API key if needed

### "API Error: 429 Too Many Requests"

**Cause**: Exceeded Salling Group API rate limit (10,000 requests/day)

**Solutions**:
- Wait a few minutes before trying again
- The system caches responses for 24h to minimize API calls
- Check if you have other applications using the same API key

### "Gemini API Error"

**Possible Causes**:
- Invalid Google API key
- Rate limit exceeded (60 requests/minute)
- Network connectivity issues

**Solutions**:
1. Verify your Google API key in `.env` file
2. Wait a minute if you've made many requests
3. Check your internet connection
4. Ensure Gemini API is enabled in your Google Cloud project

### "Invalid coordinates"

**Cause**: Latitude or longitude values are out of valid range

**Solutions**:
- Latitude must be between -90 and 90
- Longitude must be between -180 and 180
- Use decimal format (e.g., 55.6761, not 55°40'34"N)
- Try using the "Use My Location" button instead

### No results displayed after clicking "Find Meals"

**Solutions**:
1. Open browser console (F12) to check for JavaScript errors
2. Check terminal/console for Python errors
3. Verify both API keys are configured in `.env`
4. Restart the Flask server: `python app.py`
5. Clear browser cache and reload page

### Geolocation not working

**Cause**: Browser doesn't have location permission

**Solutions**:
- Click the location icon in browser address bar
- Allow location access when prompted
- If blocked, go to browser settings and enable location for localhost
- Alternatively, manually enter coordinates

## API Status & Monitoring

**Check Salling Group API Status**:
- Visit: https://developer.sallinggroup.com/
- Check for service announcements
- Verify your API key is active in your account dashboard

**Check Gemini API Status**:
- Visit: https://status.cloud.google.com/
- Look for "Vertex AI" or "Generative AI" services

## Debug Mode

Enable detailed logging by modifying `app.py`:

```python
# Add at the top of app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed API requests, responses, and processing steps in the terminal.

## Getting Help

If you encounter issues not covered here:

1. Check the terminal/console for error messages
2. Review the API documentation:
   - Salling Group: https://developer.sallinggroup.com/api-reference
   - Gemini: https://ai.google.dev/gemini-api/docs
3. Verify your `.env` file has both API keys configured
4. Try the demo scripts to test individual components:
   - `python demo.py` - Test basic workflow
   - `python demo_optimized_meals.py` - Test meal generation
