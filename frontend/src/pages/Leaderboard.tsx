import { useEffect, useState } from 'react';
import { Trophy, Medal } from 'lucide-react';
import { fetchTests, fetchLeaderboard, Test, LeaderboardEntry } from '../api/client';

function Leaderboard() {
  const [tests, setTests] = useState<Test[]>([]);
  const [selectedTestId, setSelectedTestId] = useState('');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [testName, setTestName] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTests()
      .then((t) => {
        setTests(t);
        if (t.length > 0) setSelectedTestId(t[0].id);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedTestId) return;
    setLoading(true);
    fetchLeaderboard(selectedTestId)
      .then((res) => {
        setEntries(res.entries);
        setTestName(res.test_name);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedTestId]);

  const getRankStyle = (rank: number) => {
    if (rank === 1) return 'text-yellow-500';
    if (rank === 2) return 'text-gray-400';
    if (rank === 3) return 'text-amber-600';
    return 'text-gray-300';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Trophy className="w-6 h-6 text-yellow-500" />
        <h1 className="text-2xl font-bold text-gray-900">Leaderboard</h1>
      </div>

      {/* Test selector */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Test
        </label>
        <select
          value={selectedTestId}
          onChange={(e) => setSelectedTestId(e.target.value)}
          className="border border-gray-300 rounded-md text-sm px-3 py-2 w-full max-w-xs focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">-- Choose a test --</option>
          {tests.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} (Max: {t.max_marks})
            </option>
          ))}
        </select>
      </div>

      {/* Leaderboard table */}
      {loading ? (
        <div className="p-8 text-center text-gray-500">Loading leaderboard...</div>
      ) : entries.length === 0 ? (
        <div className="p-8 text-center text-gray-500">
          {selectedTestId ? 'No scored attempts for this test yet.' : 'Select a test above.'}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h2 className="text-sm font-medium text-gray-700">
              {testName} — {entries.length} students ranked
            </h2>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-16">Rank</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Student</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Score</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Accuracy</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Net Correct</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">C / W / S</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {entries.map((e) => (
                <tr key={e.student_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className={`flex items-center gap-1 font-bold ${getRankStyle(e.rank)}`}>
                      {e.rank <= 3 && <Medal className="w-4 h-4" />}
                      {e.rank}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">{e.full_name}</div>
                    <div className="text-xs text-gray-500">{e.email || e.phone || '—'}</div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-lg font-bold text-indigo-600">{e.score}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-700">
                    {e.accuracy}%
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-700">
                    {e.net_correct}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    <span className="text-green-600">{e.correct}</span>
                    {' / '}
                    <span className="text-red-600">{e.wrong}</span>
                    {' / '}
                    <span className="text-gray-400">{e.skipped}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500">
                    {e.submitted_at
                      ? new Date(e.submitted_at).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Leaderboard;
