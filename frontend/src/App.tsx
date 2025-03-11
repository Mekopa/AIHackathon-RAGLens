import { useState } from 'react'
import { ThemeProvider } from './contexts/ThemeContext';
import './styles/themes.css';


function App() {

  return (
    <ThemeProvider>
      <div className='bg-surface'>
        What's up World
      </div>
    </ThemeProvider>

  )
}

export default App
