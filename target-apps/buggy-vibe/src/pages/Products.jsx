import { useState, useEffect } from 'react';
import './Products.css';

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      // Use relative URL - Vite proxy handles routing to backend
      const response = await fetch('/products');
      if (!response.ok) {
        throw new Error('Failed to fetch products');
      }
      const data = await response.json();
      setProducts(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="products-page"><p>Loading products...</p></div>;
  }

  if (error) {
    return (
      <div className="products-page">
        <p className="error-message">Error: {error}</p>
        <p>Make sure to run: npm run server</p>
      </div>
    );
  }

  return (
    <div className="products-page">
      <h1>Product Catalog</h1>
      {/* BUG: Visual bug - this heading overlaps with products grid */}
      <h2 className="buggy-subtitle">Browse Our Amazing Collection</h2>
      <div className="products-grid">
        {products.map((product) => (
          <div key={product.id} className="product-card">
            <div className="product-image-placeholder">
              <span>{product.category}</span>
            </div>
            <h3>{product.name}</h3>
            <p className="product-description">{product.description}</p>
            <div className="product-footer">
              <span className="product-price">${product.price}</span>
              <button className="add-to-cart-btn">Add to Cart</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Products;
