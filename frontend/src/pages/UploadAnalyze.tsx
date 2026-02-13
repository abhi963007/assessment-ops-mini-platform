import { useState, useRef, useCallback } from 'react';
import {
  Upload, FileJson, FileSpreadsheet, BarChart3, Users, BookOpen,
  Clock, AlertTriangle, CheckCircle2, XCircle, Loader2, ArrowRight,
  FileUp, Trash2, PieChart, TrendingUp,
} from 'lucide-react';
import {
  uploadAndAnalyze, uploadAndIngest, resetDatabase,
  FileAnalysis, IngestResponse,
} from '../api/client';

type Step = 'upload' | 'analyzing' | 'analyzed' | 'ingesting' | 'ingested';

function UploadAnalyze() {
  const [step, setStep] = useState<Step>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [analysis, setAnalysis] = useState<FileAnalysis | null>(null);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clearFirst, setClearFirst] = useState(false);
  const [clearing, setClearing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    const name = f.name.toLowerCase();
    if (!name.endsWith('.json') && !name.endsWith('.csv')) {
      setError('Please upload a .json or .csv file');
      return;
    }
    setError(null);
    setFile(f);
    setAnalysis(null);
    setIngestResult(null);
    setStep('upload');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleAnalyze = async () => {
    if (!file) return;
    setStep('analyzing');
    setError(null);
    try {
      const res = await uploadAndAnalyze(file);
      setAnalysis(res.analysis);
      setStep('analyzed');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Analysis failed';
      setError(msg);
      setStep('upload');
    }
  };

  const handleIngest = async () => {
    if (!file) return;
    setStep('ingesting');
    setError(null);
    try {
      if (clearFirst) {
        setClearing(true);
        await resetDatabase();
        setClearing(false);
      }
      const res = await uploadAndIngest(file);
      setIngestResult(res);
      setStep('ingested');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Ingestion failed';
      setError(msg);
      setClearing(false);
      setStep('analyzed');
    }
  };

  const reset = () => {
    setFile(null);
    setAnalysis(null);
    setIngestResult(null);
    setError(null);
    setStep('upload');
  };

  const fileIcon = file?.name.endsWith('.csv')
    ? <FileSpreadsheet className="w-8 h-8 text-green-500" />
    : <FileJson className="w-8 h-8 text-blue-500" />;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <Upload className="w-6 h-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">Upload & Analyze</h1>
      </div>
      <p className="text-sm text-gray-500">
        Upload a <strong>.json</strong> or <strong>.csv</strong> file with assessment data.
        We'll analyze it first, then you can choose to ingest it into the database.
      </p>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Upload zone */}
      {(step === 'upload' || step === 'analyzing') && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
            dragOver
              ? 'border-indigo-400 bg-indigo-50'
              : file
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300 bg-white hover:border-indigo-300 hover:bg-gray-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />

          {file ? (
            <div className="flex flex-col items-center gap-3">
              {fileIcon}
              <div>
                <p className="text-lg font-semibold text-gray-900">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <div className="flex gap-3 mt-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAnalyze();
                  }}
                  disabled={step === 'analyzing'}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                >
                  {step === 'analyzing' ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</>
                  ) : (
                    <><BarChart3 className="w-4 h-4" /> Analyze File</>
                  )}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); reset(); }}
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Trash2 className="w-4 h-4" /> Remove
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <FileUp className="w-12 h-12 text-gray-300" />
              <div>
                <p className="text-lg font-medium text-gray-700">
                  Drop your file here or <span className="text-indigo-600">browse</span>
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  Supports .json and .csv files
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Analysis Results */}
      {analysis && (step === 'analyzed' || step === 'ingesting' || step === 'ingested') && (
        <div className="space-y-4">
          {/* Summary header */}
          <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">Analysis Complete</h2>
                <p className="text-indigo-100 text-sm mt-1">
                  {analysis.filename} ({analysis.file_size_kb} KB)
                </p>
              </div>
              <BarChart3 className="w-10 h-10 text-indigo-200" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
              <StatCard label="Total Events" value={analysis.total_events} icon={<FileJson className="w-5 h-5" />} />
              <StatCard label="Unique Students" value={analysis.unique_students} icon={<Users className="w-5 h-5" />} />
              <StatCard label="Tests Found" value={analysis.tests.length} icon={<BookOpen className="w-5 h-5" />} />
              <StatCard label="Potential Dups" value={analysis.potential_duplicate_groups} icon={<AlertTriangle className="w-5 h-5" />} />
            </div>
          </div>

          {/* Detail cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Tests breakdown */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-indigo-500" /> Tests Breakdown
              </h3>
              <div className="space-y-2">
                {analysis.tests.map((t) => (
                  <div key={t.name} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="text-sm font-medium text-gray-800">{t.name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-500">Max: {t.max_marks}</span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                        {t.count} attempts
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Answer distribution */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-3">
                <PieChart className="w-4 h-4 text-purple-500" /> Answer Distribution
              </h3>
              <div className="space-y-2">
                {analysis.top_answers.map((a) => {
                  const pct = analysis.total_answers > 0
                    ? ((a.count / analysis.total_answers) * 100).toFixed(1)
                    : '0';
                  const color = a.answer === 'SKIP' ? 'bg-gray-200' :
                    a.answer === 'A' ? 'bg-blue-400' :
                    a.answer === 'B' ? 'bg-green-400' :
                    a.answer === 'C' ? 'bg-yellow-400' :
                    a.answer === 'D' ? 'bg-red-400' : 'bg-purple-400';
                  return (
                    <div key={a.answer} className="flex items-center gap-3">
                      <span className="w-12 text-xs font-mono font-bold text-gray-700">{a.answer}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${color} transition-all`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-20 text-right">
                        {a.count} ({pct}%)
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="mt-3 pt-3 border-t border-gray-100 flex justify-between text-xs text-gray-500">
                <span>Total answers: {analysis.total_answers}</span>
                <span>Skip rate: {analysis.skip_rate_percent}%</span>
              </div>
            </div>

            {/* Duration stats */}
            {analysis.duration_stats && (
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-3">
                  <Clock className="w-4 h-4 text-orange-500" /> Duration Stats
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-orange-600">
                      {analysis.duration_stats.avg_minutes ?? '—'}
                    </p>
                    <p className="text-xs text-gray-500">Avg (min)</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-600">
                      {analysis.duration_stats.min_minutes ?? '—'}
                    </p>
                    <p className="text-xs text-gray-500">Min (min)</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-red-600">
                      {analysis.duration_stats.max_minutes ?? '—'}
                    </p>
                    <p className="text-xs text-gray-500">Max (min)</p>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                  Based on {analysis.duration_stats.sample_count} attempts with valid timestamps
                </p>
              </div>
            )}

            {/* Date range */}
            {analysis.date_range && (
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2 mb-3">
                  <TrendingUp className="w-4 h-4 text-teal-500" /> Date Range
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Earliest</span>
                    <span className="font-medium text-gray-800">
                      {new Date(analysis.date_range.earliest).toLocaleDateString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Latest</span>
                    <span className="font-medium text-gray-800">
                      {new Date(analysis.date_range.latest).toLocaleDateString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Span</span>
                    <span className="font-medium text-gray-800">
                      {analysis.date_range.span_days} days
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Channels */}
            {analysis.channels && Object.keys(analysis.channels).length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Channels</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(analysis.channels).map(([ch, cnt]) => (
                    <span
                      key={ch}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium bg-blue-50 text-blue-700"
                    >
                      {ch} <span className="text-blue-400">({cnt})</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Quick stats */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Quick Stats</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Avg questions/attempt</span>
                  <span className="font-medium">{analysis.avg_questions_per_attempt}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Unique emails</span>
                  <span className="font-medium">{analysis.unique_emails}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Unique phones</span>
                  <span className="font-medium">{analysis.unique_phones}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Answered (non-skip)</span>
                  <span className="font-medium">{analysis.answered_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Skipped</span>
                  <span className="font-medium">{analysis.skip_count}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Ingest action */}
          {step === 'analyzed' && (
            <div className="bg-white rounded-lg border border-indigo-200 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">Ready to ingest?</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    This will process {analysis.total_events} events: normalize students,
                    deduplicate, and compute scores.
                  </p>
                </div>
                <button
                  onClick={handleIngest}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors flex-shrink-0"
                >
                  <ArrowRight className="w-4 h-4" /> Ingest into Database
                </button>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={clearFirst}
                  onChange={(e) => setClearFirst(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <span className="text-sm text-gray-600">
                  Clear existing data before importing
                </span>
                <span className="text-xs text-gray-400">(fresh start — removes all previous attempts)</span>
              </label>
            </div>
          )}

          {step === 'ingesting' && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-5 flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
              <span className="text-sm font-medium text-indigo-700">
                {clearing
                  ? 'Clearing existing data...'
                  : `Ingesting ${analysis.total_events} events... This may take a moment.`}
              </span>
            </div>
          )}

          {/* Ingest results */}
          {step === 'ingested' && ingestResult && (
            <div className="bg-white rounded-lg border border-green-200 p-5 space-y-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <h3 className="font-semibold text-gray-900">Ingestion Complete!</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-3xl font-bold text-green-600">{ingestResult.ingested}</p>
                  <p className="text-xs text-gray-500 mt-1">Ingested & Scored</p>
                </div>
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <p className="text-3xl font-bold text-yellow-600">{ingestResult.duplicates}</p>
                  <p className="text-xs text-gray-500 mt-1">Duplicates Found</p>
                </div>
                {ingestResult.skipped > 0 && (
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <p className="text-3xl font-bold text-blue-600">{ingestResult.skipped}</p>
                    <p className="text-xs text-gray-500 mt-1">Already Existed</p>
                  </div>
                )}
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <p className="text-3xl font-bold text-red-600">{ingestResult.errors}</p>
                  <p className="text-xs text-gray-500 mt-1">Errors</p>
                </div>
              </div>

              {/* Show first few errors if any */}
              {ingestResult.errors > 0 && (
                <div className="bg-red-50 rounded-lg p-3">
                  <p className="text-xs font-medium text-red-700 mb-2">Error details:</p>
                  <ul className="space-y-1">
                    {ingestResult.results
                      .filter((r) => r.status === 'ERROR')
                      .slice(0, 5)
                      .map((r, i) => (
                        <li key={i} className="text-xs text-red-600">
                          <span className="font-mono">{r.source_event_id}</span>:{' '}
                          {r.message.includes('started_at')
                            ? 'Invalid date/time format in the event data'
                            : r.message.length > 120
                              ? r.message.slice(0, 120) + '...'
                              : r.message}
                        </li>
                      ))}
                  </ul>
                </div>
              )}

              {/* Skipped info */}
              {ingestResult.skipped > 0 && (
                <div className="bg-blue-50 rounded-lg p-3 text-xs text-blue-700">
                  {ingestResult.skipped} events were already in the database and were skipped.
                  Use the "Clear existing data" checkbox for a fresh import.
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={reset}
                  className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50"
                >
                  <Upload className="w-4 h-4" /> Upload Another File
                </button>
                <a
                  href="/"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
                >
                  View Attempts <ArrowRight className="w-4 h-4" />
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <div className="bg-white/10 backdrop-blur rounded-lg p-3">
      <div className="flex items-center gap-2 text-indigo-100 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

export default UploadAnalyze;
