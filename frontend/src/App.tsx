import { useState, useEffect, useCallback } from 'react';
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import {
  ClipboardList, Trophy, Upload, Trash2, Database,
  AlertTriangle, X, Activity, Users, BookOpen, CheckCircle2,
} from 'lucide-react';
import AttemptsList from './pages/AttemptsList';
import AttemptDetail from './pages/AttemptDetail';
import Leaderboard from './pages/Leaderboard';
import UploadAnalyze from './pages/UploadAnalyze';
import { fetchStats, resetDatabase, DbStats } from './api/client';

function App() {
  const [stats, setStats] = useState<DbStats | null>(null);
  const [showClearModal, setShowClearModal] = useState(false);
  const [clearing, setClearing] = useState(false);
  const navigate = useNavigate();

  const loadStats = useCallback(async () => {
    try {
      const s = await fetchStats();
      setStats(s);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const handleClear = async () => {
    setClearing(true);
    try {
      await resetDatabase();
      await loadStats();
      setShowClearModal(false);
      navigate('/upload');
    } catch { /* ignore */ }
    setClearing(false);
  };

  const navItems = [
    { to: '/', label: 'Attempts', icon: ClipboardList, end: true },
    { to: '/upload', label: 'Upload & Analyze', icon: Upload },
    { to: '/leaderboard', label: 'Leaderboard', icon: Trophy },
  ];

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col">
      {/* Top Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-200/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Activity className="w-4.5 h-4.5 text-white" />
              </div>
              <span className="font-bold text-lg bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Assessment Ops
              </span>
            </div>

            {/* Nav Links */}
            <div className="flex items-center gap-1">
              {navItems.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                      isActive
                        ? 'bg-indigo-50 text-indigo-700 shadow-sm shadow-indigo-100'
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{label}</span>
                </NavLink>
              ))}
            </div>

            {/* Right: Stats + Clear */}
            <div className="flex items-center gap-3">
              {stats?.has_data && (
                <div className="hidden md:flex items-center gap-3 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5" /> {stats.total_students}
                  </span>
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-3.5 h-3.5" /> {stats.total_tests}
                  </span>
                  <span className="flex items-center gap-1">
                    <Database className="w-3.5 h-3.5" /> {stats.total_attempts}
                  </span>
                </div>
              )}
              {stats?.has_data && (
                <button
                  onClick={() => setShowClearModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                  title="Clear all data"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Clear DB</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Routes>
          <Route path="/" element={<AttemptsList />} />
          <Route path="/upload" element={<UploadAnalyze onIngestComplete={loadStats} />} />
          <Route path="/attempts/:id" element={<AttemptDetail />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
        </Routes>
      </main>

      {/* Clear DB Modal */}
      {showClearModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full mx-4 animate-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Clear All Data?</h3>
                <p className="text-sm text-gray-500">This cannot be undone.</p>
              </div>
              <button onClick={() => setShowClearModal(false)} className="ml-auto text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-1">
              This will permanently delete:
            </p>
            <ul className="text-sm text-gray-600 mb-5 space-y-1 ml-4">
              <li>• <strong>{stats?.total_attempts}</strong> attempts</li>
              <li>• <strong>{stats?.total_students}</strong> students</li>
              <li>• <strong>{stats?.total_tests}</strong> tests</li>
              <li>• All scores, flags, and duplicate links</li>
            </ul>
            <div className="flex gap-3">
              <button
                onClick={() => setShowClearModal(false)}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleClear}
                disabled={clearing}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {clearing ? (
                  <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Clearing...</>
                ) : (
                  <><Trash2 className="w-4 h-4" /> Clear Everything</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
