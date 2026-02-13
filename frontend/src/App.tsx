import { Routes, Route, NavLink } from 'react-router-dom';
import { ClipboardList, Trophy, LayoutDashboard, Upload } from 'lucide-react';
import AttemptsList from './pages/AttemptsList';
import AttemptDetail from './pages/AttemptDetail';
import Leaderboard from './pages/Leaderboard';
import UploadAnalyze from './pages/UploadAnalyze';

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2">
              <LayoutDashboard className="w-5 h-5 text-indigo-600" />
              <span className="font-semibold text-lg text-gray-900">
                Assessment Ops
              </span>
            </div>
            <div className="flex gap-1">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                <ClipboardList className="w-4 h-4" />
                Attempts
              </NavLink>
              <NavLink
                to="/upload"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                <Upload className="w-4 h-4" />
                Upload & Analyze
              </NavLink>
              <NavLink
                to="/leaderboard"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                <Trophy className="w-4 h-4" />
                Leaderboard
              </NavLink>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Routes>
          <Route path="/" element={<AttemptsList />} />
          <Route path="/upload" element={<UploadAnalyze />} />
          <Route path="/attempts/:id" element={<AttemptDetail />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
