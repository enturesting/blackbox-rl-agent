import { useState } from 'react';
import './Contact.css';

function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);
  const [submitFailed, setSubmitFailed] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // BUG: Missing validation - allows submission of empty data
    // No validation check here intentionally
    
    // BUG: Functional bug - submit occasionally fails randomly
    const shouldFail = Math.random() < 0.3; // 30% chance to fail
    
    if (shouldFail) {
      setSubmitFailed(true);
      setSubmitted(false);
      // The button doesn't trigger proper action on failure
      console.error('Form submission failed randomly');
      return;
    }

    try {
      // Use relative URL - Vite proxy handles routing to backend
      const response = await fetch('/contacts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setSubmitted(true);
        setSubmitFailed(false);
        setFormData({ name: '', email: '', message: '' });
      }
    } catch (error) {
      console.error('Error submitting form:', error);
      setSubmitFailed(true);
    }
  };

  return (
    <div className="contact-page">
      <h1>Contact Us</h1>
      <p className="contact-intro">
        Have questions? We'd love to hear from you. Send us a message and we'll respond as soon as possible.
      </p>

      <div className="contact-container">
        <form onSubmit={handleSubmit} className="contact-form">
          <div className="form-group">
            <label htmlFor="name">Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Your name"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="your.email@example.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="message">Message</label>
            <textarea
              id="message"
              name="message"
              value={formData.message}
              onChange={handleChange}
              placeholder="Your message"
              rows="5"
            />
          </div>

          <button type="submit" className="submit-btn">
            Send Message
          </button>

          {submitted && (
            <p className="success-message">
              Thank you! Your message has been sent successfully.
            </p>
          )}

          {submitFailed && (
            <p className="error-message">
              Oops! Something went wrong. Please try again.
            </p>
          )}
        </form>

        <div className="contact-info">
          <h2>Get in Touch</h2>
          <div className="info-item">
            <h3>Email</h3>
            <p>support@buggyvibe.com</p>
          </div>
          <div className="info-item">
            <h3>Phone</h3>
            <p>+1 (555) 123-4567</p>
          </div>
          <div className="info-item">
            <h3>Address</h3>
            <p>123 Test Street<br />San Francisco, CA 94102</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Contact;
