# AAT Demo Planning Brief

Test URL: {{url}}

## Page List
- / (Home): "Welcome to AAT Demo", Register/Login buttons
- /register: Enter Name, Email, Password → Register button → "Registration successful" on success
- /login: Enter Email, Password → Login button → Navigate to /main on success
- /main: Display "Welcome, {name}!", Home/Logout buttons
- /logout: End session → Navigate to /, "logged out" message

## Test Cases
1. Signup: /register → Name "Test User", Email "test@example.com", Password "password123" → Click Register → Verify "Registration successful"
2. Login: /login → Email "test@example.com", Password "password123" → Click Login → Verify navigation to /main
3. Logout: After login, click Logout → Verify navigation to /
