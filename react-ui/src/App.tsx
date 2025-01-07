import React from 'react';
import './App.css';
import DataForm from './components/DataForm';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>AP Developer</h1>
      </header>
      <main>
        <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
          <DataForm />
        </div>
      </main>
    </div>
  );
}

export default App;
