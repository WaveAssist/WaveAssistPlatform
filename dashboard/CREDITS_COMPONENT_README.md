# Credits Component

## Overview
The Credits component is a React-based page that displays credit information for the WaveAssist dashboard. It's designed to match the UI shown in the provided image with a clean, modern interface.

## Features

### 1. Credit Balance Display
- Large, prominent display of available credits
- Information icon in the top-right corner
- Clean, card-based design

### 2. Buy Credits Section
- "Buy Credits" card with crypto toggle option
- "Add Credits" button (purple/lavender styling)
- "View Usage" link with external link icon
- Toggle switch for crypto payment option

### 3. Credit Statistics
- Total Limit display
- Used credits display  
- Remaining credits display
- Color-coded values (green for total, yellow for used, blue for remaining)

## Files Created

### 1. `src/components/project/credits_component.tsx`
Main React component that handles:
- Fetching credit data from API
- Displaying credit information
- Handling user interactions
- PostHog analytics tracking

### 2. `src/components/project/credits_component.css`
Styling file that provides:
- Clean, modern card-based design
- Responsive layout
- Dark theme support
- Hover effects and transitions

### 3. `src/services/credits_services.tsx`
Service layer that handles:
- API calls to fetch credit data
- Mock data for testing (currently enabled)
- Error handling

## API Integration

### Current Implementation
The component now uses the real OpenRouter credits API:
- **Endpoint**: `https://api.waveassist.io/fetch_openrouter_credits/{uid}/`
- **Method**: POST
- **Parameters**: UID from localStorage
- **Response**: JSON with limit, usage, and limit_remaining

### API Response Format
```json
{
    "success": "1",
    "data": {
        "limit": 21,
        "usage": 16.0976049825,
        "limit_remaining": 4.902395017500002
    },
    "status": "200",
    "message": "OpenRouter credits fetched successfully."
}
```

### Error Handling
- Validates UID exists in localStorage
- Uses existing base service error handling
- Displays user-friendly error messages via toast notifications

## Routing

The component is accessible at `/manage/credits` and has been added to:
- Main App.tsx routing
- Sidebar navigation with credit card icon

## Styling

The component uses a combination of:
- Bootstrap classes for layout and basic styling
- Custom CSS for specific design requirements
- Dark theme support that matches the existing dashboard
- Responsive design for different screen sizes

## Analytics

The component includes PostHog analytics tracking for:
- Page views
- Add credits button clicks
- View usage link clicks

## Future Enhancements

1. **Real API Integration**: Connect to actual credits API endpoint
2. **Payment Processing**: Implement actual credit purchase functionality
3. **Usage Details**: Add detailed usage breakdown page
4. **Auto-refresh**: Add automatic data refresh at intervals
5. **Notifications**: Add low credit warnings
6. **Export**: Add ability to export credit usage data

## Usage

To access the credits page:
1. Navigate to the dashboard
2. Click on "Credits" in the sidebar navigation
3. View your current credit balance and usage
4. Use the "Add Credits" button to purchase more credits

## Dependencies

- React
- Bootstrap
- Bootstrap Icons
- PostHog (for analytics)
- React Router (for navigation)
