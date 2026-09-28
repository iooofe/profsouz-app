import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

// iOS Safari ignores user-scalable=no, so pinch-zoom is blocked on the gesture itself:
// a zoomed page pans sideways and pushes the bottom navigation off screen.
['gesturestart', 'gesturechange', 'gestureend'].forEach((type) => {
  document.addEventListener(type, (event) => event.preventDefault(), { passive: false });
});

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
