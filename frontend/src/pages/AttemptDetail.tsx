import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, Flag, ChevronDown, ChevronUp, Copy,
} from 'lucide-react';
import {
  fetchAttempt, fetchDuplicateThread, recomputeScore, flagAttempt,
  Attempt,
} from '../api/client';

const STATUS_COLORS: Record<string, string> = {
  SCORED: 'bg-green-100 text-green-800',
  DEDUPED: 'bg-yellow-100 text-yellow-800',
  FLAGGED: 'bg-red-100 text-red-800',
  INGESTED: 'bg-blue-100 text-blue-800',
};

function AttemptDetail() {
  const { id } = useParams<{ id: string }>();
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [dupThread, setDupThread] = useState<{
    canonical: Attempt;
    duplicates: Attempt[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [rawOpen, setRawOpen] = useState(false);
  const [flagReason, setFlagReason] = useState('');
  const [flagging, setFlagging] = useState(false);
  const [recomputing, setRecomputing] = useState(false);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [a, dt] = await Promise.all([
        fetchAttempt(id),
        fetchDuplicateThread(id),
      ]);
      setAttempt(a);
      setDupThread(dt);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleRecompute = async () => {
    if (!id) return;
    setRecomputing(true);
    try {
      await recomputeScore(id);
      await load();
    } catch (e) {
      console.error(e);
    } finally {
      setRecomputing(false);
    }
  };

  const handleFlag = async () => {
    if (!id || !flagReason.trim()) return;
    setFlagging(true);
    try {
      await flagAttempt(id, flagReason.trim());
      setFlagReason('');
      await load();
    } catch (e) {
      console.error(e);
    } finally {
      setFlagging(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading...</div>;
  }

  if (!attempt) {
    return <div className="p-8 text-center text-red-500">Attempt not found.</div>;
  }

  const score = attempt.score;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Attempt Detail</h1>
        <span
          className={`ml-2 inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
            STATUS_COLORS[attempt.status] || 'bg-gray-100'
          }`}
        >
          {attempt.status}
        </span>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Student info */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-medium text-gray-500 mb-2">Student</h2>
          <p className="text-lg font-semibold">{attempt.student?.full_name}</p>
          <p className="text-sm text-gray-600">{attempt.student?.email || '—'}</p>
          <p className="text-sm text-gray-600">{attempt.student?.phone || '—'}</p>
        </div>

        {/* Test info */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-medium text-gray-500 mb-2">Test</h2>
          <p className="text-lg font-semibold">{attempt.test?.name}</p>
          <p className="text-sm text-gray-600">Max marks: {attempt.test?.max_marks}</p>
          <p className="text-sm text-gray-600">
            Started: {new Date(attempt.started_at).toLocaleString('en-IN')}
          </p>
          <p className="text-sm text-gray-600">
            Submitted: {attempt.submitted_at
              ? new Date(attempt.submitted_at).toLocaleString('en-IN')
              : 'Not submitted'}
          </p>
        </div>
      </div>

      {/* Score breakdown */}
      {score && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-medium text-gray-500 mb-3">Score Breakdown</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-indigo-600">{score.score}</p>
              <p className="text-xs text-gray-500">Score</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{score.correct}</p>
              <p className="text-xs text-gray-500">Correct</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{score.wrong}</p>
              <p className="text-xs text-gray-500">Wrong</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-600">{score.skipped}</p>
              <p className="text-xs text-gray-500">Skipped</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{score.accuracy}%</p>
              <p className="text-xs text-gray-500">Accuracy</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">{score.net_correct}</p>
              <p className="text-xs text-gray-500">Net Correct</p>
            </div>
          </div>
          {score.explanation && (
            <div className="mt-3 p-3 bg-gray-50 rounded text-xs font-mono text-gray-600 overflow-x-auto">
              {JSON.stringify(score.explanation, null, 2)}
            </div>
          )}
        </div>
      )}

      {/* Duplicate thread */}
      {dupThread && (dupThread.duplicates.length > 0 || attempt.duplicate_of_attempt_id) && (
        <div className="bg-white rounded-lg border border-yellow-200 p-4">
          <h2 className="text-sm font-medium text-yellow-700 mb-3 flex items-center gap-1">
            <Copy className="w-4 h-4" /> Duplicate Thread
          </h2>
          <div className="space-y-2">
            {/* Canonical */}
            <div className="flex items-center gap-2 p-2 bg-green-50 rounded text-sm">
              <span className="font-medium text-green-800">Canonical:</span>
              <Link
                to={`/attempts/${dupThread.canonical.id}`}
                className="text-indigo-600 hover:underline font-mono text-xs"
              >
                {dupThread.canonical.id.slice(0, 8)}...
              </Link>
              <span className="text-gray-500">
                {dupThread.canonical.source_event_id}
              </span>
            </div>
            {/* Duplicates */}
            {dupThread.duplicates.map((d) => (
              <div
                key={d.id}
                className="flex items-center gap-2 p-2 bg-yellow-50 rounded text-sm"
              >
                <span className="font-medium text-yellow-800">Duplicate:</span>
                <Link
                  to={`/attempts/${d.id}`}
                  className="text-indigo-600 hover:underline font-mono text-xs"
                >
                  {d.id.slice(0, 8)}...
                </Link>
                <span className="text-gray-500">{d.source_event_id}</span>
                {d.score && (
                  <span className="text-gray-400 ml-auto">
                    score: {d.score.score}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-4 items-end">
        <button
          onClick={handleRecompute}
          disabled={recomputing}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${recomputing ? 'animate-spin' : ''}`} />
          {recomputing ? 'Recomputing...' : 'Recompute Score'}
        </button>

        <div className="flex items-end gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Flag reason</label>
            <input
              type="text"
              value={flagReason}
              onChange={(e) => setFlagReason(e.target.value)}
              placeholder="e.g. Suspicious activity"
              className="border border-gray-300 rounded-md text-sm px-3 py-2 w-64 focus:ring-red-500 focus:border-red-500"
            />
          </div>
          <button
            onClick={handleFlag}
            disabled={flagging || !flagReason.trim()}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            <Flag className="w-4 h-4" />
            {flagging ? 'Flagging...' : 'Flag'}
          </button>
        </div>
      </div>

      {/* Flags list */}
      {attempt.flags && attempt.flags.length > 0 && (
        <div className="bg-white rounded-lg border border-red-200 p-4">
          <h2 className="text-sm font-medium text-red-700 mb-2">Flags</h2>
          <ul className="space-y-1">
            {attempt.flags.map((f) => (
              <li key={f.id} className="text-sm text-gray-700">
                <span className="font-medium">{f.reason}</span>
                <span className="text-gray-400 ml-2">
                  {new Date(f.created_at).toLocaleString('en-IN')}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Raw payload (collapsible) */}
      <div className="bg-white rounded-lg border border-gray-200">
        <button
          onClick={() => setRawOpen(!rawOpen)}
          className="w-full flex items-center justify-between p-4 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Raw Payload
          {rawOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {rawOpen && (
          <div className="p-4 pt-0">
            <pre className="bg-gray-50 rounded p-3 text-xs font-mono text-gray-600 overflow-x-auto max-h-96 overflow-y-auto">
              {JSON.stringify(attempt.answers, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default AttemptDetail;
