# BuggyVibe 🐛

A React-based web application intentionally designed with bugs for AI QA testing purposes.

## 🎯 Purpose

BuggyVibe is a testing playground for AI-powered QA systems. The application contains intentional bugs across different categories to help test and train automated testing tools.

## 🛠️ Tech Stack

- **Frontend**: React 19 with Vite
- **Routing**: React Router DOM
- **Mock Backend**: json-server
- **Styling**: Custom CSS

## 📋 Features

- **Home Page**: Welcome section with hero banner and feature highlights
- **Products Page**: Product catalog fetched from mock database
- **Contact Page**: Contact form with submission handling
- **Login Page**: User authentication form (vulnerable to SQL injection)
- **Responsive Design**: Mobile-friendly layouts

## 🐞 Intentional Bugs (For QA Testing)

This application contains the following intentional bugs:

1. **Broken Links**: 
   - "About" link in navbar leads to 404
   - "Privacy Policy" link in footer leads to 404

2. **Visual Bug**:
   - Product page subtitle overlaps with the product grid due to negative margin

3. **Functional Bugs**:
   - Contact form accepts empty submissions (no validation)
   - Submit button has 30% random failure rate

4. **Media Bug**:
   - Home page contains broken image URL displaying alt text

5. **Console Error**:
   - Home page logs tracking error to console

6. **Security Vulnerabilities** (when using vulnerable server):
   - **SQL Injection**: User search and login endpoints vulnerable to SQL injection
   - **Data Exposure**: Cleartext passwords stored in pw_db.json
   - **Debug Endpoint**: Exposed database schema at /api/debug/schema
   - **No Input Validation**: User ID endpoint accepts any input

## 🚀 Getting Started

### Prerequisites

- Node.js (v18 or higher)
- npm

### Quick Setup (Copy & Paste)

```bash
# === STEP 1: Clone and Navigate ===
git clone https://github.com/enturesting/buggy-vibe.git
cd buggy-vibe

# === STEP 2: Install Dependencies ===
npm install

# === STEP 3: Start Backend (New Terminal) ===
# For SQL injection testing (RECOMMENDED):
npm run server:vulnerable

# Or for basic functionality only:
# npm run server

# === STEP 4: Start Frontend (Another New Terminal) ===
npm run dev

# === DONE! ===
# Frontend: http://localhost:5173
# Backend:  http://localhost:3001
```

### Test Credentials

```
Normal Login:
- Username: admin / Password: admin123
- Username: john_doe / Password: password123

SQL Injection (Login Page):
- Username: admin' OR '1'='1' --
- Password: anything

SQL Injection (User Search):
- Search: ' OR '1'='1' --
- Search: ' UNION SELECT * FROM users --
```

### Running the Application (Detailed)

You need **TWO terminal windows** running simultaneously:

**Terminal 1 - Backend Server**
```bash
# Navigate to project
cd buggy-vibe

# Choose ONE of these:
npm run server:vulnerable  # Recommended - includes SQL injection endpoints
# OR
npm run server            # Basic server without vulnerabilities
```

**Terminal 2 - Frontend**
```bash
# Navigate to project
cd buggy-vibe

# Start React app
npm run dev
```

**Access Points:**
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:3001`

**Important**: Both servers must be running at the same time!

## 📁 Project Structure

```
buggy-vibe/
├── src/
│   ├── components/       # Reusable components (Navbar, Footer)
│   ├── pages/           # Page components (Home, Products, Contact, NotFound)
│   ├── App.jsx          # Main app component with routing
│   ├── App.css          # Global app styles
│   ├── index.css        # Base styles
│   └── main.jsx         # App entry point
├── db.json              # Mock database for json-server
├── package.json         # Project dependencies and scripts
└── README.md           # This file
```

## 🧪 Testing the Bugs

### Test Case 1: Broken Links
1. Navigate to any page
2. Click "About" in navbar or "Privacy Policy" in footer
3. Expected: 404 page appears

### Test Case 2: Visual Overlap Bug
1. Navigate to Products page
2. Expected: Subtitle overlaps with first row of products

### Test Case 3: Form Validation Bug
1. Navigate to Contact page
2. Click "Send Message" without filling any fields
3. Expected: Form submits successfully with empty data

### Test Case 4: Random Submit Failure
1. Navigate to Contact page
2. Fill out form and submit multiple times
3. Expected: Approximately 30% of submissions fail randomly

### Test Case 5: Broken Image
1. Navigate to Home page
2. Expected: Broken image icon/alt text visible in hero section

### Test Case 6: Console Error
1. Open browser console
2. Navigate to Home page
3. Expected: Red error message about tracking failure

### Test Case 7: SQL Injection - User Search (requires vulnerable server)
1. Start the vulnerable server (`npm run server:vulnerable`)
2. Make a GET request to: `http://localhost:3001/api/users/search?username=' OR '1'='1' --`
3. Expected: Returns all users from the database instead of no results

### Test Case 8: SQL Injection - Login Bypass (requires vulnerable server)
1. Start the vulnerable server
2. Make a POST request to `http://localhost:3001/api/login` with:
   ```json
   {
     "username": "admin' OR '1'='1' --",
     "password": "anything"
   }
   ```
3. Expected: Successfully logs in as admin user without correct password

### Test Case 9: Data Exposure - Debug Endpoint
1. Start the vulnerable server
2. Navigate to: `http://localhost:3001/api/debug/schema`
3. Expected: Exposes entire database schema information

### Test Case 10: Cleartext Password Storage
1. View the `pw_db.json` file
2. Expected: All passwords are stored in cleartext (not hashed)

## 📦 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run server` - Start json-server mock backend
- `npm run server:vulnerable` - Start vulnerable server with SQL injection endpoints

## 🎨 Styling Approach

The application uses vanilla CSS with a modular approach:
- Component-specific CSS files
- Consistent color scheme
- Responsive design patterns
- Modern flexbox/grid layouts

## 📝 API Endpoints

### Standard Endpoints (json-server)
- `GET /products` - Fetch all products
- `POST /contacts` - Submit contact form

### Vulnerable Endpoints (vulnerable server only)
- `GET /api/users/search?username=xxx` - SQL injection vulnerable user search
- `POST /api/login` - SQL injection vulnerable login endpoint
- `GET /api/users/:id` - User endpoint with no input validation
- `GET /api/debug/schema` - Exposed debug endpoint showing database schema

## 🤝 Contributing

This is a testing application with intentional bugs. If you find bugs not listed in the documentation, they might be unintentional! Feel free to report them.

## 📄 License

MIT License - Feel free to use this for testing and educational purposes.
