import React, { useState } from "react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { Loader2 } from "lucide-react";
import "./App.css";

const AppContent: React.FC = () => {
  const { token, loading } = useAuth();
  const [showRegister, setShowRegister] = useState(false);

  // 1. Loading state (Authenticating localStorage token)
  if (loading) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-[#070b13] text-slate-100">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500 mb-3" />
        <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Loading credentials...</span>
      </div>
    );
  }

  // 2. Unauthenticated state (Form toggler)
  if (!token) {
    if (showRegister) {
      return <Register onToggleForm={() => setShowRegister(false)} />;
    }
    return <Login onToggleForm={() => setShowRegister(true)} />;
  }

  // 3. Authenticated state
  return <Dashboard />;
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
