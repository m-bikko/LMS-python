#!/usr/bin/env python3
import requests
import time

def test_web_csv_export():
    """Test the CSV export functionality through the web interface"""
    
    base_url = "http://127.0.0.1:5002"
    
    # Give the server a moment to start
    time.sleep(2)
    
    # Test if server is running
    try:
        response = requests.get(base_url)
        print(f"Server status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("Server is not running. Please start the application first.")
        return
    
    # Create a session
    session = requests.Session()
    
    # Login as teacher
    login_data = {
        'email': 'teacher@gmail.com',  # Teacher with courses
        'password': 'teacherpass'
    }
    
    # Get login page first to get any CSRF token if needed
    login_page = session.get(f"{base_url}/login")
    print(f"Login page status: {login_page.status_code}")
    
    # Login
    login_response = session.post(f"{base_url}/login", data=login_data)
    print(f"Login response status: {login_response.status_code}")
    
    if login_response.status_code == 200 and "dashboard" in login_response.url:
        print("✓ Successfully logged in as teacher")
    else:
        print("✗ Failed to login")
        print(f"Response URL: {login_response.url}")
        return
    
    # Navigate to teacher dashboard
    dashboard_response = session.get(f"{base_url}/teacher/dashboard")
    print(f"Teacher dashboard status: {dashboard_response.status_code}")
    
    # Test CSV export for course 1
    course_id = 1
    
    # First, check course students page
    students_page = session.get(f"{base_url}/teacher/courses/{course_id}/students")
    print(f"Course students page status: {students_page.status_code}")
    
    if students_page.status_code == 200:
        print("✓ Successfully accessed course students page")
        
        # Check if export button exists in HTML
        if "Export Progress CSV" in students_page.text:
            print("✓ Export CSV button found on page")
        else:
            print("✗ Export CSV button not found on page")
    
    # Test the actual CSV export
    export_response = session.get(f"{base_url}/teacher/courses/{course_id}/export-progress")
    print(f"CSV export response status: {export_response.status_code}")
    
    if export_response.status_code == 200:
        print("✓ CSV export successful")
        print(f"Content-Type: {export_response.headers.get('Content-Type')}")
        print(f"Content-Disposition: {export_response.headers.get('Content-Disposition')}")
        
        # Save the CSV content to check it
        csv_content = export_response.text
        print(f"\nCSV Content Preview (first 500 chars):")
        print(csv_content[:500])
        
        # Save to file
        filename = f"web_export_test_{int(time.time())}.csv"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        print(f"\nCSV saved to: {filename}")
        
    else:
        print("✗ CSV export failed")
        print(f"Response content: {export_response.text[:200]}")

if __name__ == '__main__':
    test_web_csv_export() 