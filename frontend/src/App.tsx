import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { AuthModal } from './components/AuthModal';

import { HomePage } from './pages/HomePage';
import { MastersCatalogPage } from './pages/MastersCatalogPage';
import { MasterDetailPage } from './pages/MasterDetailPage';
import { BecomeMasterPage } from './pages/BecomeMasterPage';
import { MasterDashboardPage } from './pages/MasterDashboardPage';
import { UserDashboardPage } from './pages/UserDashboardPage';
import { ChatPage } from './pages/ChatPage';
import { AuthPage } from './pages/AuthPage';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans selection:bg-blue-600 selection:text-white">
          <Navbar />
          
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/masters" element={<MastersCatalogPage />} />
              <Route path="/masters/:id" element={<MasterDetailPage />} />
              <Route path="/become-master" element={<BecomeMasterPage />} />
              <Route path="/master/dashboard" element={<MasterDashboardPage />} />
              <Route path="/dashboard" element={<UserDashboardPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/login" element={<AuthPage />} />
              <Route path="/register" element={<AuthPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          <Footer />

          {/* Global guest auth modal triggered from any call, chat, or rating action */}
          <AuthModal />
        </div>
      </Router>
    </AuthProvider>
  );
};

export default App;
