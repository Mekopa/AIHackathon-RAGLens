// src/App.tsx

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import DocHubPage from './pages/DocHub';
import './styles/themes.css';

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <Routes>
          <Route path="/" element={<DocHubPage />} />
          {/* Add more routes as needed */}
        </Routes>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;