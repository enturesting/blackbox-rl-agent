import { useState } from 'react';
import './Login.css';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [userData, setUserData] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Use relative URL - Vite proxy handles routing to backend
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();
      
      if (response.ok) {
        setMessage(`Login successful! Welcome ${data.user.username} (${data.user.role})`);
        setUserData(data);
      } else {
        setMessage(`Login failed: ${data.error}`);
        setUserData(null);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
      setUserData(null);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Login</h1>
        <p className="vulnerability-hint">
          🐛 Hint: This login form is vulnerable to SQL injection. Try: <code>admin' OR '1'='1' --</code>
        </p>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username:</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
          </div>
          
          <button type="submit" className="login-button">Login</button>
        </form>

        {message && (
          <div className={`message ${message.includes('successful') ? 'success' : 'error'}`}>
            {message}
          </div>
        )}

        {userData && (
          <div className="user-data">
            <h3>Response Data:</h3>
            <pre>{JSON.stringify(userData, null, 2)}</pre>
          </div>
        )}

        <div className="test-users">
          <h3>Test Users (when not using SQL injection):</h3>
          <ul>
            <li>admin / admin123</li>
            <li>john_doe / password123</li>
            <li>guest / guest</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Login;
