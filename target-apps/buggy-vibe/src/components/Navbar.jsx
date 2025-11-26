import { Link } from 'react-router-dom';
import './Navbar.css';

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          BuggyVibe
        </Link>
        <ul className="navbar-menu">
          <li>
            <Link to="/" className="navbar-link">Home</Link>
          </li>
          <li>
            <Link to="/products" className="navbar-link">Products</Link>
          </li>
          <li>
            <Link to="/contact" className="navbar-link">Contact</Link>
          </li>
          <li>
            <Link to="/login" className="navbar-link">Login</Link>
          </li>
          <li>
            <Link to="/users" className="navbar-link">Users</Link>
          </li>
          {/* BUG: Broken link to non-existent page */}
          <li>
            <Link to="/about-us" className="navbar-link">About</Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}

export default Navbar;
