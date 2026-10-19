import React from 'react';
import { createRoot } from 'react-dom/client';
import Console from './Console';
import LegacyApp from './App';
const App = import.meta.env.VITE_AGENTVERSE_LEGACY_UI === '1' ? LegacyApp : Console;
import './style.css';
import '@xyflow/react/dist/style.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode>
    <App />
</React.StrictMode>);
