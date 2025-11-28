const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const app = express();

// Enable CORS for frontend
app.use(cors());
app.use(express.json());

// Load user database from pw_db.json
let dbData = { users: [] };
try {
  const dbPath = path.join(__dirname, 'pw_db.json');
  dbData = JSON.parse(fs.readFileSync(dbPath, 'utf8'));
  console.log(`✅ Loaded ${dbData.users.length} users from pw_db.json`);
} catch (err) {
  console.error('⚠️  Could not load pw_db.json, using empty database');
}

const users = dbData.users;

// Vulnerable user search endpoint (SQL injection vulnerable)
app.get('/api/users/search', (req, res) => {
  const { username } = req.query;
  
  console.log(`[VULNERABLE] Searching for username: ${username}`);
  
  // Simulate SQL injection vulnerability
  if (username && username.includes("' OR '1'='1'")) {
    console.log('[SQL INJECTION DETECTED] Returning all users with passwords!');
    return res.json({
      vulnerable: true,
      message: 'SQL Injection successful! Database dumped with passwords!',
      users: users,
      api_keys: dbData.api_keys || [],
      sessions: dbData.sessions || []
    });
  }
  
  if (username && username.includes('UNION SELECT')) {
    console.log('[UNION ATTACK DETECTED] Returning database schema');
    return res.json({
      vulnerable: true,
      message: 'UNION attack successful! Database schema exposed.',
      schema: {
        tables: ['users', 'products', 'orders', 'sessions'],
        users_columns: ['id', 'username', 'password_hash', 'email', 'role', 'created_at']
      },
      users: users
    });
  }
  
  // Normal search
  const results = users.filter(user => 
    user.username.toLowerCase().includes((username || '').toLowerCase())
  );
  
  res.json({ users: results });
});

// Products endpoint (from db.json)
const products = [
  { id: "1", name: "Wireless Headphones", price: 79.99, category: "Electronics", description: "High-quality wireless headphones with noise cancellation" },
  { id: "2", name: "Smart Watch", price: 199.99, category: "Electronics", description: "Feature-rich smartwatch with fitness tracking" },
  { id: "3", name: "Coffee Maker", price: 49.99, category: "Home", description: "Programmable coffee maker with thermal carafe" },
  { id: "4", name: "Running Shoes", price: 89.99, category: "Sports", description: "Lightweight running shoes with excellent cushioning" },
  { id: "5", name: "Desk Lamp", price: 29.99, category: "Home", description: "LED desk lamp with adjustable brightness" }
];

app.get('/products', (req, res) => {
  res.json(products);
});

// Vulnerable login endpoint (SQL injection vulnerable)
app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  
  console.log(`[LOGIN ATTEMPT] Username: ${username}, Password: ${password}`);
  
  // Simulate SQL injection vulnerability in login
  if (username && (username.includes("' OR '1'='1'") || username.includes("admin' --"))) {
    console.log('[SQL INJECTION IN LOGIN] Authentication bypassed!');
    return res.json({
      success: true,
      message: 'SQL Injection successful! Authentication bypassed.',
      user: {
        id: 1,
        username: 'admin',
        email: 'admin@buggyvibe.com',
        role: 'admin',
        token: 'vulnerable-token-12345'
      }
    });
  }
  
  // Normal login check (simplified)
  const user = users.find(u => u.username === username);
  if (user && password === 'password123') {
    return res.json({
      success: true,
      user: {
        ...user,
        token: `token-${user.id}`
      }
    });
  }
  
  res.status(401).json({
    success: false,
    message: 'Invalid credentials'
  });
});

// Contacts endpoint
app.get('/contacts', (req, res) => {
  res.json([]);
});

app.post('/contacts', (req, res) => {
  console.log('Contact form submission:', req.body);
  res.json({ id: Date.now().toString(), ...req.body });
});

const PORT = 3001;
app.listen(PORT, () => {
  console.log(`🚨 Vulnerable server running on http://localhost:${PORT}`);
  console.log('⚠️  WARNING: This server contains intentional security vulnerabilities!');
  console.log('📍 Endpoints:');
  console.log('   - POST /api/login (SQL injection vulnerable)');
  console.log('   - GET /api/users/search?username=xxx (SQL injection vulnerable)');
  console.log('   - GET /products');
  console.log('   - GET /contacts');
  console.log('   - POST /contacts');
});
