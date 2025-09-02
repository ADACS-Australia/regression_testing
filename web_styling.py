#!/usr/bin/env python3
"""
Web styling module for Quokka regression testing.
Provides enhanced CSS, responsive design, and branding elements.
"""

def get_enhanced_css() -> str:
    """
    Get enhanced CSS with responsive design, dark mode support, and modern styling.
    Note: Curly braces are doubled for Python format() compatibility.
    
    Returns:
        String containing the complete CSS stylesheet
    """
    return """
        /* CSS Reset and Base Styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {
            /* Light mode colors */
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #e9ecef;
            --text-primary: #212529;
            --text-secondary: #495057;
            --text-muted: #6c757d;
            --border-color: #dee2e6;
            --accent-color: #0066cc;  /* Darker blue for better contrast (WCAG AA) */
            --accent-hover: #0052a3;  /* Even darker on hover */
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --shadow-sm: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
            --shadow-md: 0 0.5rem 1rem rgba(0,0,0,0.15);
            --shadow-lg: 0 1rem 3rem rgba(0,0,0,0.175);
        }
        
        /* Dark mode - applied via class or media query */
        [data-theme="dark"],
        :root:not([data-theme="light"]) {
            --bg-primary: #1a1a1a;
            --bg-secondary: #2d2d2d;
            --bg-tertiary: #3a3a3a;
            --text-primary: #e9ecef;
            --text-secondary: #adb5bd;
            --text-muted: #868e96;
            --border-color: #495057;
            --accent-color: #4dabf7;
            --accent-hover: #339af0;
            --shadow-sm: 0 0.125rem 0.25rem rgba(0,0,0,0.5);
            --shadow-md: 0 0.5rem 1rem rgba(0,0,0,0.7);
            --shadow-lg: 0 1rem 3rem rgba(0,0,0,0.9);
        }
        
        /* Auto dark mode detection when no manual preference set */
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme]) {
                --bg-primary: #1a1a1a;
                --bg-secondary: #2d2d2d;
                --bg-tertiary: #3a3a3a;
                --text-primary: #e9ecef;
                --text-secondary: #adb5bd;
                --text-muted: #868e96;
                --border-color: #495057;
                --accent-color: #4dabf7;
                --accent-hover: #339af0;
                --shadow-sm: 0 0.125rem 0.25rem rgba(0,0,0,0.5);
                --shadow-md: 0 0.5rem 1rem rgba(0,0,0,0.7);
                --shadow-lg: 0 1rem 3rem rgba(0,0,0,0.9);
            }
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        /* General link styles for better legibility */
        a {
            color: var(--accent-color);
            text-decoration: none;
            transition: color 0.2s ease, opacity 0.2s ease;
        }
        
        a:hover {
            color: var(--accent-hover);
            text-decoration: underline;
        }
        
        a:visited {
            color: var(--accent-color);
            opacity: 0.9;
        }
        
        a:active {
            opacity: 0.7;
        }
        
        /* Container and Layout */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: var(--bg-primary);
            padding: 30px;
            border-radius: 12px;
            box-shadow: var(--shadow-md);
            animation: fadeIn 0.5s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Theme Toggle Button */
        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--bg-secondary);
            border: 2px solid var(--border-color);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 1000;
            box-shadow: var(--shadow-md);
        }
        
        .theme-toggle:hover {
            background: var(--bg-tertiary);
            transform: scale(1.1);
            box-shadow: var(--shadow-lg);
        }
        
        .theme-toggle svg {
            width: 24px;
            height: 24px;
            fill: var(--text-primary);
            transition: transform 0.3s ease;
        }
        
        .theme-toggle:hover svg {
            transform: rotate(20deg);
        }
        
        /* Header with Logos */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid var(--accent-color);
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .logo-container {
            display: flex;
            align-items: center;
            gap: 30px;
        }
        
        .logo {
            height: 60px;
            width: auto;
            filter: brightness(0) saturate(100%) opacity(0.8);
            transition: filter 0.3s ease;
        }
        
        .logo:hover {
            filter: brightness(0) saturate(100%) opacity(1);
        }
        
        @media (prefers-color-scheme: dark) {
            .logo {
                filter: brightness(100%) saturate(100%) opacity(0.9);
            }
            .logo:hover {
                filter: brightness(100%) saturate(100%) opacity(1);
            }
        }
        
        /* Typography */
        h1 {
            color: var(--text-primary);
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0;
            background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        h2 {
            color: var(--text-secondary);
            font-size: 1.75rem;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--border-color);
        }
        
        h3 {
            color: var(--text-secondary);
            font-size: 1.25rem;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        /* Navigation */
        .nav-links {
            background: var(--bg-secondary);
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: center;
        }
        
        .nav-links a {
            color: var(--accent-color);
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            padding: 5px 10px;
            border-radius: 4px;
        }
        
        .nav-links a:hover {
            background: var(--accent-color);
            color: white;
            transform: translateY(-2px);
        }
        
        /* Cards and Grids */
        .folder-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }
        
        .folder-card {
            background: var(--bg-secondary);
            padding: 25px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        
        .folder-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-color), var(--success-color));
            transform: translateX(-100%);
            transition: transform 0.3s ease;
        }
        
        .folder-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-lg);
        }
        
        .folder-card:hover::before {
            transform: translateX(0);
        }
        
        .folder-card h3 {
            margin-top: 0;
            color: var(--text-primary);
            font-size: 1.5rem;
        }
        
        .folder-card .stats {
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid var(--border-color);
        }
        
        .folder-card .stat {
            text-align: center;
        }
        
        .folder-card .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent-color);
        }
        
        .folder-card .stat-label {
            font-size: 0.875rem;
            color: var(--text-muted);
        }
        
        /* Timestamp List */
        .timestamp-list {
            list-style: none;
            padding: 0;
        }
        
        .timestamp-list li {
            background: var(--bg-secondary);
            margin: 15px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid var(--accent-color);
            transition: all 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .timestamp-list li:hover {
            transform: translateX(5px);
            box-shadow: var(--shadow-md);
        }
        
        .timestamp-list a {
            color: var(--accent-color);
            text-decoration: none;
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .timestamp-list .date {
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        
        .timestamp-list .badge {
            background: var(--accent-color);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.875rem;
        }
        
        /* Summary Boxes */
        .performance-summary, .comparison-summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 25px 0;
            box-shadow: var(--shadow-md);
        }
        
        .performance-summary h3, .comparison-summary h3 {
            color: white;
            margin-top: 0;
            margin-bottom: 15px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }
        
        .summary-item {
            text-align: center;
            padding: 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }
        
        .summary-value {
            font-size: 2rem;
            font-weight: bold;
        }
        
        .summary-label {
            font-size: 0.875rem;
            opacity: 0.9;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 25px 0;
            background: var(--bg-primary);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }
        
        th {
            background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.875rem;
            letter-spacing: 0.5px;
        }
        
        td {
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
        }
        
        tr:last-child td {
            border-bottom: none;
        }
        
        tr:hover {
            background: var(--bg-secondary);
        }
        
        /* Status badges */
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-passed {
            background: var(--success-color);
            color: white;
        }
        
        .status-failed {
            background: var(--danger-color);
            color: white;
        }
        
        .status-pending {
            background: var(--warning-color);
            color: var(--text-primary);
        }
        
        /* Plots */
        .plot-container {
            margin: 30px 0;
            padding: 25px;
            background: var(--bg-secondary);
            border-radius: 10px;
            box-shadow: var(--shadow-sm);
        }
        
        .plot-container h3 {
            margin-top: 0;
            color: var(--text-primary);
        }
        
        /* Warning and Info boxes */
        .warning {
            background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
            color: var(--text-primary);
            padding: 20px;
            border-radius: 10px;
            margin: 25px 0;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .warning::before {
            content: '⚠️';
            font-size: 1.5rem;
        }
        
        /* Footer */
        .footer {
            margin-top: 60px;
            padding-top: 25px;
            border-top: 2px solid var(--border-color);
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
        }
        
        .footer a {
            color: var(--accent-color);
            text-decoration: none;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            
            h1 {
                font-size: 1.75rem;
            }
            
            h2 {
                font-size: 1.5rem;
            }
            
            .header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .logo-container {
                width: 100%;
                justify-content: center;
            }
            
            .logo {
                height: 40px;
            }
            
            .folder-grid {
                grid-template-columns: 1fr;
            }
            
            table {
                font-size: 0.875rem;
            }
            
            th, td {
                padding: 10px;
            }
            
            /* Make tables scrollable on mobile */
            .table-wrapper {
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }
        }
        
        @media (max-width: 480px) {
            body {
                padding: 10px;
            }
            
            .container {
                padding: 15px;
                border-radius: 8px;
            }
            
            h1 {
                font-size: 1.5rem;
            }
            
            .nav-links {
                flex-direction: column;
                align-items: stretch;
            }
            
            .nav-links a {
                display: block;
                text-align: center;
            }
        }
        
        /* Print styles */
        @media print {
            body {
                background: white;
            }
            
            .container {
                box-shadow: none;
                padding: 0;
            }
            
            .nav-links {
                display: none;
            }
            
            .logo-container {
                display: none;
            }
        }
        
        /* Animations */
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .update-badge {
            animation: pulse 2s infinite;
        }
        
        /* Loading spinner */
        .spinner {
            border: 3px solid var(--border-color);
            border-top: 3px solid var(--accent-color);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    """


def get_theme_toggle_html() -> str:
    """
    Get HTML and JavaScript for theme toggle button.
    
    Returns:
        HTML string with theme toggle button and script
    """
    return """
    <!-- Theme Toggle Button -->
    <button class="theme-toggle" id="theme-toggle" aria-label="Toggle theme">
        <svg class="sun-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="display: none;">
            <path d="M12 17.5C9.5 17.5 7.5 15.5 7.5 13S9.5 8.5 12 8.5 16.5 10.5 16.5 13 14.5 17.5 12 17.5M12 7C8.7 7 6 9.7 6 13S8.7 19 12 19 18 16.3 18 13 15.3 7 12 7M12 2L14.4 6.4L19 5.7L16.2 9.8L18.6 14L14 12.3L9.4 14L11.8 9.8L9 5.7L13.6 6.4L12 2Z"/>
        </svg>
        <svg class="moon-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="display: none;">
            <path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95M17.33,17.97C14.5,17.81 11.7,16.64 9.53,14.5C7.36,12.31 6.2,9.5 6.04,6.68C3.23,9.82 3.34,14.64 6.35,17.66C9.37,20.67 14.19,20.78 17.33,17.97Z"/>
        </svg>
    </button>
    
    <script>
        // Theme toggle functionality
        (function() {{
            const toggle = document.getElementById('theme-toggle');
            const sunIcon = toggle.querySelector('.sun-icon');
            const moonIcon = toggle.querySelector('.moon-icon');
            const root = document.documentElement;
            
            // Get saved theme or detect preference
            function getTheme() {{
                const saved = localStorage.getItem('theme');
                if (saved) {{
                    return saved;
                }}
                return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            }}
            
            // Set theme
            function setTheme(theme) {{
                root.setAttribute('data-theme', theme);
                localStorage.setItem('theme', theme);
                updateIcon(theme);
            }}
            
            // Update icon based on theme
            function updateIcon(theme) {{
                if (theme === 'dark') {{
                    sunIcon.style.display = 'block';
                    moonIcon.style.display = 'none';
                }} else {{
                    sunIcon.style.display = 'none';
                    moonIcon.style.display = 'block';
                }}
            }}
            
            // Initialize theme
            const currentTheme = getTheme();
            setTheme(currentTheme);
            
            // Toggle theme on click
            toggle.addEventListener('click', function() {{
                const current = root.getAttribute('data-theme');
                const newTheme = current === 'dark' ? 'light' : 'dark';
                setTheme(newTheme);
            }});
        }})();
    </script>
    """

def get_logo_html() -> str:
    """
    Get HTML for QUOKKA and ADACS logos.
    Uses inline SVG for the logos so they work without external files.
    
    Returns:
        HTML string with logo elements
    """
    return """
    <div class="logo-container">
        <!-- QUOKKA Logo (placeholder SVG) -->
        <svg class="logo quokka-logo" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
            <text x="10" y="40" font-family="Arial, sans-serif" font-size="32" font-weight="bold" fill="currentColor">QUOKKA</text>
        </svg>
        
        <!-- ADACS Logo (placeholder SVG) -->
        <svg class="logo adacs-logo" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
            <text x="10" y="40" font-family="Arial, sans-serif" font-size="32" font-weight="bold" fill="currentColor">ADACS</text>
        </svg>
    </div>
    """


def get_enhanced_html_template() -> str:
    """
    Get enhanced HTML template with modern structure and metadata.
    
    Returns:
        HTML template string with placeholders for title and content
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Quokka Regression Testing Dashboard - Performance metrics and analysis">
    <meta name="author" content="QUOKKA Team">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    {theme_toggle}
    <div class="container">
        <div class="header">
            <div>
                <h1>{heading}</h1>
            </div>
            {logos}
        </div>
        
        {content}
        
        <div class="footer">
            <p>Generated on {timestamp} | Quokka Regression Testing Dashboard</p>
            <p>
                <a href="https://github.com/quokka-astro/quokka" target="_blank">Quokka on GitHub</a> | 
                <a href="https://adacs.org.au" target="_blank">ADACS</a>
            </p>
        </div>
    </div>
</body>
</html>"""


def wrap_in_responsive_table(html_table: str) -> str:
    """
    Wrap a table in a responsive container for mobile viewing.
    
    Args:
        html_table: The table HTML to wrap
        
    Returns:
        HTML string with responsive wrapper
    """
    return f'<div class="table-wrapper">{html_table}</div>'