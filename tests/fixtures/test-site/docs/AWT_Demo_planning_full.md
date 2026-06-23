# AAT Demo Web Application Planning Document

## Overview
Flask-based web application, a demo site providing signup/login/logout functionality.
Test URL: {{url}}

## Page Structure

### 1. Home (/)
- Display "Welcome to AAT Demo" title
- "Register" button → Navigate to /register
- "Login" button → Navigate to /login
- Navigation: Home, Register, Login links

### 2. Signup (/register)
- "Create Account" title
- Input fields:
  - Name (text, required)
  - Email (email, required)
  - Password (password, required)
- "Register" button (light green) → Process signup
- On signup success: "Registration successful" message, navigate to /login
- Bottom: "Already have an account? Login here" link

### 3. Login (/login)
- "Login" title
- Input fields:
  - Email (email, required)
  - Password (password, required)
- "Login" button (blue) → Process login
- On login success: Navigate to /main
- On login failure: Display error message
- Bottom: "Don't have an account? Register here" link

### 4. Main (/main) - After Login
- "Welcome, {username}!" title
- "Home" button → Navigate to /
- "Logout" button (red) → Process logout
- Navigation: Home, Main, Logout links

### 5. Logout (/logout)
- Redirect to / after session end
- Display "You have been logged out" message

## Test Scenario Requirements

### TC-001: Signup
1. Navigate to /register page
2. Enter "Test User" in Name
3. Enter "test@example.com" in Email
4. Enter "password123" in Password
5. Click Register button
6. Verify "Registration successful" message

### TC-002: Login
1. Navigate to /login page
2. Enter "test@example.com" in Email
3. Enter "password123" in Password
4. Click Login button
5. Verify navigation to /main page
6. Verify "Welcome" text

### TC-003: Main Page Navigation
1. Verify /main page while logged in
2. Click Home button → Verify navigation to /
3. Click Main link → Verify navigation to /main

### TC-004: Logout
1. Click Logout while logged in
2. Verify navigation to / page
3. Verify "logged out" message

### TC-005: Input Validation
1. Click Register with empty fields on /register page
2. Verify required input validation
3. Enter invalid email format then click Register
4. Verify email format validation
