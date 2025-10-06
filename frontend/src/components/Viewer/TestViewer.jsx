import React from 'react';
import { useParams } from 'react-router-dom';

export default function TestViewer() {
  const { studyId } = useParams();
  
  return (
    <div style={{ padding: '20px', backgroundColor: '#1a1a1a', color: 'white', minHeight: '100vh' }}>
      <h1>Test Viewer</h1>
      <p>Study ID: {studyId}</p>
      <p>If you can see this, React routing is working.</p>
      <div style={{ border: '1px solid white', width: '200px', height: '200px', backgroundColor: 'red' }}>
        Red Test Box
      </div>
    </div>
  );
}