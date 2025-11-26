import { Link } from 'react-router-dom';
import './Footer.css';

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-section">
          <h3>BuggyVibe</h3>
          <p>Your one-stop shop for testing purposes.</p>
        </div>
        <div className="footer-section">
          <h4>Quick Links</h4>
          <ul>
            <li><Link to="/">Home</Link></li>
            <li><Link to="/products">Products</Link></li>
            <li><Link to="/contact">Contact</Link></li>
            {/* BUG: Another broken link */}
            <li><Link to="/privacy-policy">Privacy Policy</Link></li>
          </ul>
        </div>
        <div className="footer-section">
          <h4>Follow Us</h4>
          <p>Connect with us on social media</p>
        </div>
      </div>
      <div className="footer-bottom">
        <p>&copy; 2024 BuggyVibe. All rights reserved.</p>
      </div>
    </footer>
  );
}

export default Footer;
