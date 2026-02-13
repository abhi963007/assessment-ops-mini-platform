import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Filter, ChevronLeft, ChevronRight, Copy, AlertTriangle } from 'lucide-react';
import { fetchAttempts, fetchTests, Attempt, Test } from '../api/client';

const STATUS_COLORS: Record<string, string> = {
  SCORED: 'bg-green-100 text-green-800',
  DEDUPED: 'bg-yellow-100 text-yellow-800',
  FLAGGED: 'bg-red-100 text-red-800',
  INGESTED: 'bg-blue-100 text-blue-800',
};

function AttemptsList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [total, setTotal] = useState(0);
  const [tests, setTests] = useState<Test[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters from URL
  const page = parseInt(searchParams.get('page') || '1', 10);
  const pageSize = 20;
  const statusFilter = searchParams.get('status') || '';
  const testFilter = searchParams.get('test_id') || '';
  const dupFilter = searchParams.get('has_duplicates') || '';
  const searchQuery = searchParams.get('search') || '';

  useEffect(() => {
    fetchTests().then(setTests).catch(console.error);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params: Record<string, unknown> = { page, page_size: pageSize };
    if (statusFilter) params.status = statusFilter;
    if (testFilter) params.test_id = testFilter;
    if (dupFilter) params.has_duplicates = dupFilter === 'true';
    if (searchQuery) params.search = searchQuery;

    fetchAttempts(params as Parameters<typeof fetchAttempts>[0])
      .then((res) => {
        if (!cancelled) {
          setAttempts(res.items);
          setTotal(res.total);
        }
      })
      .catch((err) => { if (!cancelled) console.error(err); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [page, statusFilter, testFilter, dupFilter, searchQuery]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Attempts</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center bg-white p-4 rounded-lg border border-gray-200">
        <Filter className="w-4 h-4 text-gray-400" />

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search student..."
            value={searchQuery}
            onChange={(e) => updateFilter('search', e.target.value)}
            className="pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        {/* Test filter */}
        <select
          value={testFilter}
          onChange={(e) => updateFilter('test_id', e.target.value)}
          className="border border-gray-300 rounded-md text-sm px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">All Tests</option>
          {tests.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => updateFilter('status', e.target.value)}
          className="border border-gray-300 rounded-md text-sm px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">All Statuses</option>
          <option value="SCORED">Scored</option>
          <option value="DEDUPED">Deduped</option>
          <option value="FLAGGED">Flagged</option>
          <option value="INGESTED">Ingested</option>
        </select>

        {/* Duplicates filter */}
        <select
          value={dupFilter}
          onChange={(e) => updateFilter('has_duplicates', e.target.value)}
          className="border border-gray-300 rounded-md text-sm px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">All</option>
          <option value="true">Duplicates Only</option>
          <option value="false">Non-Duplicates</option>
        </select>

        <span className="text-sm text-gray-500 ml-auto">{total} results</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : attempts.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No attempts found.</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Student</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Test</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Dup</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {attempts.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => navigate(`/attempts/${a.id}`)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">
                      {a.student?.full_name || '—'}
                    </div>
                    <div className="text-xs text-gray-500">
                      {a.student?.email || a.student?.phone || '—'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {a.test?.name || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        STATUS_COLORS[a.status] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-700">
                    {a.score ? a.score.score : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(a.started_at).toLocaleDateString('en-IN', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </td>
                  <td className="px-4 py-3">
                    {a.duplicate_of_attempt_id ? (
                      <span className="flex items-center gap-1 text-xs text-yellow-700">
                        <Copy className="w-3 h-3" /> Yes
                      </span>
                    ) : a.flags && a.flags.length > 0 ? (
                      <span className="flex items-center gap-1 text-xs text-red-600">
                        <AlertTriangle className="w-3 h-3" /> Flagged
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setSearchParams((p) => { p.set('page', String(page - 1)); return p; })}
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-md text-sm disabled:opacity-40 hover:bg-gray-50"
            >
              <ChevronLeft className="w-4 h-4" /> Prev
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setSearchParams((p) => { p.set('page', String(page + 1)); return p; })}
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-md text-sm disabled:opacity-40 hover:bg-gray-50"
            >
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AttemptsList;
