# AAT Demo Service Planning Document

## 1. Service Overview

AAT Demo is a demo web application for verifying the automated testing functionality of AI Auto Tester.
It provides basic user flows: signup, login, main page access, and logout.

## 2. Page Structure

### 2.1 Landing Page (`/`)
- **Purpose**: Service first screen, unauthenticated user guide
- **Components**:
  - "Welcome to AAT Demo" title
  - "Register" button → Navigate to signup page
  - "Login" button → Navigate to login page
- **Navigation bar**: Home, Register, Login links

### 2.2 Signup Page (`/register`)
- **Purpose**: Create new user account
- **Input fields**:
  - Name: User name (text)
  - Email: Email address (email format)
  - Password: Password (masked)
- **Button**: "Register" (form submit)
- **Validation rules**:
  - All fields required
  - Duplicate email registration not allowed
- **On success**: "Registration successful! Please login." message + navigate to login page
- **On failure**: Display error message (red background)

### 2.3 Login Page (`/login`)
- **Purpose**: Authenticate existing user
- **Input fields**:
  - Email: Email address
  - Password: Password
- **Button**: "Login" (form submit)
- **On success**: "Welcome back, {name}!" message + navigate to main page
- **On failure**: "Invalid email or password." error message

### 2.4 Main Page (`/main`)
- **Purpose**: User dashboard after login
- **Access restriction**: Login required (redirect to login page if unauthenticated)
- **Components**:
  - "Welcome, {name}!" greeting message
  - "Home" button → Navigate to landing page
  - "Logout" button → Process logout
- **Navigation bar**: Home, Main, Logout links

### 2.5 Logout (`/logout`)
- **Purpose**: Terminate user session
- **Behavior**: Clear session + redirect to landing page with "Logged out successfully." message

---

## 3. User Flow

```
Landing Page (/)
    │
    ├── [Register] → Signup Page (/register)
    │                   │
    │                   └── [Submit Form] → Login Page (/login)
    │                                              │
    │                                              └── [Submit Form] → Main Page (/main)
    │                                                                     │
    │                                                                     └── [Logout] → Landing Page (/)
    │
    └── [Login] → Login Page (/login)
                      │
                      └── [Submit Form] → Main Page (/main)
                                            │
                                            └── [Logout] → Landing Page (/)
```

## 4. Test Scenarios

### Scenario 1: New User Signup Flow
1. Navigate to `/`
2. Click "Register" button
3. Fill Name: "Test User"
4. Fill Email: "test@example.com"
5. Fill Password: "password123"
6. Click "Register"
7. Verify: Success message appears
8. Verify: Redirected to `/login`
9. Fill Email: "test@example.com"
10. Fill Password: "password123"
11. Click "Login"
12. Verify: Redirected to `/main`
13. Verify: "Welcome, Test User!" message displayed

### Scenario 2: Existing User Login Flow
1. Navigate to `/`
2. Click "Login" button
3. Fill Email: existing user email
4. Fill Password: correct password
5. Click "Login"
6. Verify: Redirected to `/main`
7. Verify: Welcome message with user name displayed

### Scenario 3: Logout Flow
1. Login to `/main`
2. Click "Logout" button
3. Verify: Redirected to `/`
4. Verify: "Logged out successfully." message displayed

## 5. Technical Specifications

- Framework: Flask (Python)
- Database: SQLite (in-memory for demo)
- Session Management: Flask-Login
- Styling: Minimal CSS for test visibility
- Deployment: Local development server (http://localhost:5000)
