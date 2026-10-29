import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard, BookOpen, CheckCircle2, GitFork, CalendarRange,
  Binary, HelpCircle, Plus, RotateCcw, AlertTriangle,
  Search, Trash2, Edit3, X, Sparkles, FileDown
} from 'lucide-react';
import { api } from './api';
import type { Course, Metrics, EligibilityResult, GraphData, SemesterPlanResult } from './types';
import './App.css';

type Page = 'dashboard' | 'courses' | 'eligibility' | 'graph' | 'planner' | 'math' | 'about';

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>(() => {
    const hash = window.location.hash.replace('#', '') as Page;
    const valid: Page[] = ['dashboard', 'courses', 'eligibility', 'graph', 'planner', 'math', 'about'];
    return valid.includes(hash) ? hash : 'dashboard';
  });

  const navigateTo = (page: Page) => {
    setCurrentPage(page);
    window.location.hash = page;
  };

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as Page;
      const valid: Page[] = ['dashboard', 'courses', 'eligibility', 'graph', 'planner', 'math', 'about'];
      if (valid.includes(hash)) {
        setCurrentPage(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);
  const [courses, setCourses] = useState<Course[]>([]);
  const [completed, setCompleted] = useState<string[]>(() => {
    const saved = localStorage.getItem('curriculogic_completed');
    return saved ? JSON.parse(saved) : [];
  });
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Course Edit/Add Modal
  const [isCourseModalOpen, setIsCourseModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [formCode, setFormCode] = useState('');
  const [formName, setFormName] = useState('');
  const [formCredits, setFormCredits] = useState(3);
  const [formPrereqs, setFormPrereqs] = useState<string[]>([]);
  const [formError, setFormError] = useState('');

  // Delete confirmation
  const [deletingCourse, setDeletingCourse] = useState<string | null>(null);

  // Planner state
  const [planMaxCredits, setPlanMaxCredits] = useState(12);
  const [planSemesters, setPlanSemesters] = useState(4);
  const [planIncludeCompleted, setPlanIncludeCompleted] = useState(false);
  const [planResult, setPlanResult] = useState<SemesterPlanResult | null>(null);
  const [planningLoading, setPlanningLoading] = useState(false);

  // Math Lab State
  const [mathTab, setMathTab] = useState<'logic' | 'relations' | 'poset' | 'toposort' | 'pigeonhole' | 'combinatorics'>('logic');
  const [truthVar, setTruthVar] = useState<string[]>(['DST', 'DSM']);
  const [truthTable, setTruthTable] = useState<Record<string, number>[]>([]);
  const [phCredits, setPhCredits] = useState(34);
  const [phMax, setPhMax] = useState(12);
  const [phSems, setPhSems] = useState(4);
  const [phCheck, setPhCheck] = useState<{ required: number; capacity: number; min_load: number; feasible: boolean } | null>(null);
  const [combN, setCombN] = useState(5);
  const [combK, setCombK] = useState(3);
  const [combResult, setCombResult] = useState<{ combinations: number; permutations: number } | null>(null);

  // Graph State
  const [graphViewMode, setGraphViewMode] = useState<'full' | 'hasse'>('full');
  const [selectedNode, setSelectedNode] = useState<string | null>('DST');

  useEffect(() => {
    localStorage.setItem('curriculogic_completed', JSON.stringify(completed));
  }, [completed]);

  const loadAllData = async () => {
    try {
      setLoading(true);
      const [cList, mData, eData, gData] = await Promise.all([
        api.getCourses(),
        api.getMetrics(completed),
        api.getEligibility(completed),
        api.getGraph(),
      ]);
      setCourses(cList);
      setMetrics(mData);
      setEligibility(eData);
      setGraphData(gData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [completed]);

  // Auto-generate plan on mount or planner select
  useEffect(() => {
    if (currentPage === 'planner' && !planResult && courses.length > 0) {
      handleGeneratePlan();
    }
  }, [currentPage, courses.length]);
  useEffect(() => {
    if (mathTab === 'logic') {
      api.getTruthTable(truthVar).then(setTruthTable).catch(console.error);
    } else if (mathTab === 'pigeonhole') {
      api.checkCapacity({ required_credits: phCredits, max_credits: phMax, semesters: phSems })
        .then(setPhCheck).catch(console.error);
    } else if (mathTab === 'combinatorics') {
      api.getCombinatorics(combN, combK).then(setCombResult).catch(console.error);
    }
  }, [mathTab, truthVar, phCredits, phMax, phSems, combN, combK]);

  const toggleCourseCompleted = (code: string) => {
    setCompleted(prev => 
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const handleOpenAdd = () => {
    setEditingCourse(null);
    setFormCode('');
    setFormName('');
    setFormCredits(3);
    setFormPrereqs([]);
    setFormError('');
    setIsCourseModalOpen(true);
  };

  const handleOpenEdit = (course: Course) => {
    setEditingCourse(course);
    setFormCode(course.code);
    setFormName(course.name);
    setFormCredits(course.credits);
    setFormPrereqs([...course.prereqs]);
    setFormError('');
    setIsCourseModalOpen(true);
  };

  const handleSaveCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = formCode.trim().toUpperCase();
    const cleanName = formName.trim();

    if (!cleanCode) return setFormError('Course code is required');
    if (!cleanName) return setFormError('Course name is required');

    let updated: Course[];
    if (editingCourse) {
      updated = courses.map(c => c.code === editingCourse.code ? {
        code: cleanCode,
        name: cleanName,
        credits: formCredits,
        prereqs: formPrereqs,
      } : c);
    } else {
      if (courses.some(c => c.code === cleanCode)) {
        return setFormError(`Course code ${cleanCode} already exists.`);
      }
      updated = [...courses, {
        code: cleanCode,
        name: cleanName,
        credits: formCredits,
        prereqs: formPrereqs,
      }];
    }

    try {
      await api.saveCourses(updated);
      setIsCourseModalOpen(false);
      await loadAllData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save course');
    }
  };

  const handleDeleteCourse = async (code: string) => {
    const updated = courses
      .filter(c => c.code !== code)
      .map(c => ({
        ...c,
        prereqs: c.prereqs.filter(p => p !== code),
      }));
    await api.saveCourses(updated);
    setCompleted(prev => prev.filter(c => c !== code));
    setDeletingCourse(null);
    await loadAllData();
  };

  const handleResetSample = async () => {
    if (window.confirm('Reset all courses to built-in sample curriculum?')) {
      await api.resetCourses();
      setCompleted([]);
      await loadAllData();
    }
  };

  const handleGeneratePlan = async () => {
    setPlanningLoading(true);
    try {
      const res = await api.planSemesters({
        max_credits: planMaxCredits,
        semesters: planSemesters,
        completed,
        include_completed: planIncludeCompleted,
      });
      setPlanResult(res);
    } catch (err: any) {
      alert(err.message || 'Planning failed');
    } finally {
      setPlanningLoading(false);
    }
  };

  const filteredCourses = courses.filter(c => 
    c.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="app-container">
      {/* ── Sidebar ── */}
      <aside className="app-sidebar">
        <div className="sidebar-header">
          <div className="logo-row">
            <div className="logo-icon">C</div>
            <div className="logo-title">Curricu<span>Logic</span></div>
          </div>
          <div className="sidebar-desc">Smart Course Prerequisite Planner</div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
            onClick={() => navigateTo('dashboard')}
          >
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'courses' ? 'active' : ''}`}
            onClick={() => navigateTo('courses')}
          >
            <BookOpen size={18} />
            <span>Course Catalog</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'eligibility' ? 'active' : ''}`}
            onClick={() => navigateTo('eligibility')}
          >
            <CheckCircle2 size={18} />
            <span>Eligibility Checker</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'graph' ? 'active' : ''}`}
            onClick={() => navigateTo('graph')}
          >
            <GitFork size={18} />
            <span>Dependency Graph</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'planner' ? 'active' : ''}`}
            onClick={() => navigateTo('planner')}
          >
            <CalendarRange size={18} />
            <span>Semester Planner</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'math' ? 'active' : ''}`}
            onClick={() => navigateTo('math')}
          >
            <Binary size={18} />
            <span>Mathematics Lab</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'about' ? 'active' : ''}`}
            onClick={() => navigateTo('about')}
          >
            <HelpCircle size={18} />
            <span>About Project</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <strong>BAMAT205</strong><br />
          Discrete Mathematics & Linear Algebra<br />
          Academic Planning Platform
        </div>
      </aside>

      {/* ── Main Viewport ── */}
      <main className="app-main">
        <header className="top-bar">
          <div className="top-bar-left">
            <span className="top-bar-title">CurricuLogic Academic Portal</span>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={handleResetSample}>
              <RotateCcw size={14} /> Restore Default Data
            </button>
          </div>
        </header>

        <div className="content-container">
          {/* ═════════ 1. DASHBOARD ═════════ */}
          {currentPage === 'dashboard' && (
            <div>
              <div className="page-header">
                <div>
                  <div className="page-eyebrow">Academic Overview</div>
                  <h1 className="page-title">Degree Planning Dashboard</h1>
                  <p className="page-subtitle">
                    Model course prerequisites as mathematical partial orders to generate conflict-free academic roadmaps.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button className="btn btn-primary" onClick={() => setCurrentPage('planner')}>
                    <CalendarRange size={16} /> Plan My Semesters
                  </button>
                  <button className="btn btn-secondary" onClick={() => setCurrentPage('eligibility')}>
                    <CheckCircle2 size={16} /> Check Eligibility
                  </button>
                </div>
              </div>

              {metrics && (
                <div className="stats-grid">
                  <div className="stat-card">
                    <span className="stat-label">Total Courses</span>
                    <span className="stat-value">{metrics.total}</span>
                    <span className="stat-sub">{metrics.total_credits} credits total</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Completed</span>
                    <span className="stat-value" style={{ color: '#166534' }}>{metrics.completed}</span>
                    <span className="stat-sub">{metrics.completed_credits} credits earned</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Eligible Now</span>
                    <span className="stat-value" style={{ color: 'var(--teal-600)' }}>{metrics.eligible}</span>
                    <span className="stat-sub">Ready to register</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Blocked</span>
                    <span className="stat-value" style={{ color: 'var(--amber-600)' }}>{metrics.blocked}</span>
                    <span className="stat-sub">{metrics.remaining_credits} credits remaining</span>
                  </div>
                </div>
              )}

              <div className="two-col-grid">
                {/* Left: Prerequisite Graph Preview */}
                <div className="card">
                  <div className="card-title">
                    <GitFork size={20} color="var(--teal-600)" />
                    <span>Prerequisite Dependency Structure</span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                    Directed topological layout: arrows run from prerequisite to dependent course.
                  </p>

                  {graphData && (
                    <div style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '16px', background: '#FAFAFA' }}>
                      <svg viewBox="-0.8 -1.8 5.6 3.6" style={{ width: '100%', height: '320px' }}>
                        <defs>
                          <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                            <path d="M 0 1 L 10 5 L 0 9 z" fill="#94A3B8" />
                          </marker>
                        </defs>
                        {/* Edges */}
                        {graphData.edges.map((e, idx) => {
                          const p1 = graphData.positions[e.source];
                          const p2 = graphData.positions[e.target];
                          if (!p1 || !p2) return null;
                          return (
                            <line
                              key={idx}
                              x1={p1.x} y1={p1.y}
                              x2={p2.x} y2={p2.y}
                              stroke="#CBD5E1"
                              strokeWidth="0.04"
                              markerEnd="url(#arrow)"
                            />
                          );
                        })}
                        {/* Nodes */}
                        {graphData.nodes.map(n => {
                          const pos = graphData.positions[n.id] || { x: 0, y: 0 };
                          const isDone = completed.includes(n.code);
                          const isElig = eligibility?.eligible.some(c => c.code === n.code);
                          let fill = '#E2E8F0';
                          let textFill = '#1E293B';
                          if (isDone) { fill = '#15803D'; textFill = '#FFF'; }
                          else if (isElig) { fill = '#0D9488'; textFill = '#FFF'; }

                          return (
                            <g key={n.id} transform={`translate(${pos.x}, ${pos.y})`}>
                              <circle r="0.32" fill={fill} stroke="#334155" strokeWidth="0.03" />
                              <text
                                textAnchor="middle"
                                dy="0.09"
                                fontSize="0.18"
                                fontWeight="bold"
                                fill={textFill}
                              >
                                {n.code}
                              </text>
                            </g>
                          );
                        })}
                      </svg>

                      <div style={{ display: 'flex', gap: '16px', marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#15803D' }} /> Completed
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#0D9488' }} /> Eligible now
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#E2E8F0', border: '1px solid #94A3B8' }} /> Blocked
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right: Ready To Take Courses */}
                <div className="card">
                  <div className="card-title">
                    <Sparkles size={20} color="var(--indigo-600)" />
                    <span>Eligible to Enroll Now</span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                    Courses whose prerequisites are 100% satisfied. Click to toggle completion:
                  </p>

                  <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
                    {eligibility?.eligible.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                        No courses eligible right now. Mark completed prerequisite courses to unlock dependents.
                      </div>
                    ) : (
                      eligibility?.eligible.map(c => (
                        <div key={c.code} className="course-item" style={{ cursor: 'pointer' }} onClick={() => toggleCourseCompleted(c.code)}>
                          <div className="course-item-header">
                            <span className="course-code">{c.code}</span>
                            <span className="badge badge-eligible">Eligible ★</span>
                          </div>
                          <div className="course-name">{c.name}</div>
                          <div className="course-meta">
                            {c.credits} Credits · {c.prereqs.length === 0 ? 'Foundational' : `Prereqs: ${c.prereqs.join(', ')}`}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ═════════ 2. COURSE CATALOG ═════════ */}
          {currentPage === 'courses' && (
            <div>
              <div className="page-header">
                <div>
                  <div className="page-eyebrow">Curriculum Data</div>
                  <h1 className="page-title">Course Management</h1>
                  <p className="page-subtitle">
                    Configure courses, credit weights, and strict prerequisite mappings.
                  </p>
                </div>
                <button className="btn btn-primary" onClick={handleOpenAdd}>
                  <Plus size={16} /> Add New Course
                </button>
              </div>

              <div className="card" style={{ marginBottom: '20px', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Search size={18} color="var(--text-muted)" />
                  <input
                    type="text"
                    placeholder="Search courses by code or title..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    style={{ flex: 1, border: 'none', outline: 'none', fontSize: '0.95rem' }}
                  />
                  {searchQuery && (
                    <button onClick={() => setSearchQuery('')} style={{ color: 'var(--text-muted)' }}>
                      <X size={16} />
                    </button>
                  )}
                </div>
              </div>

              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: '120px' }}>Code</th>
                      <th>Course Name</th>
                      <th style={{ width: '90px' }}>Credits</th>
                      <th>Prerequisites</th>
                      <th style={{ width: '130px' }}>Status</th>
                      <th style={{ width: '130px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCourses.map(c => {
                      const isDone = completed.includes(c.code);
                      const isElig = eligibility?.eligible.some(e => e.code === c.code);
                      return (
                        <tr key={c.code}>
                          <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{c.code}</td>
                          <td style={{ fontWeight: 600 }}>{c.name}</td>
                          <td>{c.credits}</td>
                          <td>
                            {c.prereqs.length === 0 ? (
                              <span style={{ color: 'var(--text-subtle)' }}>None (Foundational)</span>
                            ) : (
                              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                {c.prereqs.map(p => (
                                  <span key={p} style={{ background: '#F1F5F9', padding: '2px 6px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                                    {p}
                                  </span>
                                ))}
                              </div>
                            )}
                          </td>
                          <td>
                            {isDone ? (
                              <span className="badge badge-completed">✓ Completed</span>
                            ) : isElig ? (
                              <span className="badge badge-eligible">★ Eligible</span>
                            ) : (
                              <span className="badge badge-blocked">⊘ Blocked</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '8px' }}>
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '4px 8px' }}
                                onClick={() => handleOpenEdit(c)}
                                title="Edit course"
                              >
                                <Edit3 size={14} />
                              </button>
                              <button
                                className="btn btn-danger"
                                style={{ padding: '4px 8px' }}
                                onClick={() => setDeletingCourse(c.code)}
                                title="Delete course"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ═════════ 3. ELIGIBILITY CHECKER ═════════ */}
          {currentPage === 'eligibility' && (
            <div>
              <div className="page-header">
                <div>
                  <div className="page-eyebrow">Prerequisite Verification</div>
                  <h1 className="page-title">Eligibility Checker</h1>
                  <p className="page-subtitle">
                    Select courses you have already passed. Dependents automatically recalculate in real-time.
                  </p>
                </div>
                {completed.length > 0 && (
                  <button className="btn btn-secondary" onClick={() => setCompleted([])}>
                    Clear All Completed
                  </button>
                )}
              </div>

              {eligibility?.has_cycle && (
                <div style={{ padding: '16px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius-md)', marginBottom: '20px', color: '#B91C1C', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <AlertTriangle size={20} />
                  <span><strong>Circular Dependency Cycle Detected:</strong> {eligibility.cycle_path?.join(' → ')}. Courses involved can never become eligible!</span>
                </div>
              )}

              <div className="three-col-grid">
                {/* 1. Completed */}
                <div className="card">
                  <div className="card-title">
                    <CheckCircle2 size={18} color="#15803D" />
                    <span>Completed Courses ({eligibility?.completed.length || 0})</span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
                    Courses you have finished. Click to unmark:
                  </p>
                  {eligibility?.completed.map(c => (
                    <div
                      key={c.code}
                      className="course-item"
                      style={{ cursor: 'pointer', borderLeft: '3px solid #15803D' }}
                      onClick={() => toggleCourseCompleted(c.code)}
                    >
                      <div className="course-item-header">
                        <span className="course-code">{c.code}</span>
                        <span className="badge badge-completed">✓ Done</span>
                      </div>
                      <div className="course-name">{c.name}</div>
                      <div className="course-meta">{c.credits} Credits</div>
                    </div>
                  ))}
                  {eligibility?.completed.length === 0 && (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '24px' }}>
                      No courses marked completed yet.
                    </div>
                  )}
                </div>

                {/* 2. Eligible Now */}
                <div className="card">
                  <div className="card-title">
                    <Sparkles size={18} color="var(--teal-600)" />
                    <span>Eligible to Take ({eligibility?.eligible.length || 0})</span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
                    Prerequisites 100% satisfied. Click to mark completed:
                  </p>
                  {eligibility?.eligible.map(c => (
                    <div
                      key={c.code}
                      className="course-item"
                      style={{ cursor: 'pointer', borderLeft: '3px solid var(--teal-600)' }}
                      onClick={() => toggleCourseCompleted(c.code)}
                    >
                      <div className="course-item-header">
                        <span className="course-code">{c.code}</span>
                        <span className="badge badge-eligible">★ Ready</span>
                      </div>
                      <div className="course-name">{c.name}</div>
                      <div className="course-meta">
                        {c.credits} Credits · {c.prereqs.length === 0 ? 'Foundational' : `Prereqs: ${c.prereqs.join(', ')}`}
                      </div>
                    </div>
                  ))}
                </div>

                {/* 3. Blocked */}
                <div className="card">
                  <div className="card-title">
                    <AlertTriangle size={18} color="var(--amber-600)" />
                    <span>Blocked Courses ({eligibility?.blocked.length || 0})</span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
                    Waiting on incomplete prerequisite courses:
                  </p>
                  {eligibility?.blocked.map(c => (
                    <div key={c.code} className="course-item" style={{ borderLeft: '3px solid var(--amber-600)' }}>
                      <div className="course-item-header">
                        <span className="course-code">{c.code}</span>
                        <span className="badge badge-blocked">⊘ Blocked</span>
                      </div>
                      <div className="course-name">{c.name}</div>
                      <div className="course-meta" style={{ color: 'var(--rose-600)', fontWeight: 600 }}>
                        Missing: {c.missing_prereqs.join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ═════════ 4. DEPENDENCY GRAPH ═════════ */}
          {currentPage === 'graph' && (
            <div>
              <div className="page-header">
                <div>
                  <div className="page-eyebrow">Topological Visualization</div>
                  <h1 className="page-title">Prerequisite Dependency Graph</h1>
                  <p className="page-subtitle">
                    Interact with the directed prerequisite network or switch to the minimal Hasse transitive reduction diagram.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px', background: '#F1F5F9', padding: '4px', borderRadius: 'var(--radius-md)' }}>
                  <button
                    className={`btn ${graphViewMode === 'full' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                    onClick={() => setGraphViewMode('full')}
                  >
                    Full DAG
                  </button>
                  <button
                    className={`btn ${graphViewMode === 'hasse' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '6px 12px', fontSize: '0.82rem' }}
                    onClick={() => setGraphViewMode('hasse')}
                  >
                    Hasse Reduction
                  </button>
                </div>
              </div>

              {graphData && (() => {
                const activeEdges = graphViewMode === 'hasse' ? graphData.hasse_edges : graphData.edges;
                const selectedCourse = courses.find(c => c.code === selectedNode) || courses[0];
                const directPrereqs = selectedCourse ? selectedCourse.prereqs : [];
                const directDependents = courses.filter(c => c.prereqs.includes(selectedNode || '')).map(c => c.code);

                return (
                  <div>
                    {/* Top Stats Banner */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '20px' }}>
                      <div className="card" style={{ padding: '16px' }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Structure Type</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
                          {graphViewMode === 'hasse' ? 'Hasse Reduction' : 'Full Prerequisite DAG'}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {graphViewMode === 'hasse' ? `${graphData.redundant_edges.length} transitive edges removed` : 'All explicit requirements'}
                        </div>
                      </div>
                      <div className="card" style={{ padding: '16px' }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Active Connections</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--teal-600)', marginTop: '4px' }}>
                          {activeEdges.length} Directed Edges
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>Across {graphData.nodes.length} curriculum courses</div>
                      </div>
                      <div className="card" style={{ padding: '16px' }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Selected Course</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy-900)', marginTop: '4px' }}>
                          {selectedNode || 'Click any node'}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {directPrereqs.length} prereqs • {directDependents.length} unlockable
                        </div>
                      </div>
                      <div className="card" style={{ padding: '16px' }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Interactive Guide</div>
                        <div style={{ fontSize: '0.86rem', color: 'var(--text-main)', marginTop: '4px', lineHeight: 1.4 }}>
                          Click a node to highlight its complete upstream and downstream path.
                        </div>
                      </div>
                    </div>

                    {/* Main Layout: Graph Visualization + Inspector Panel */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px', alignItems: 'start' }}>
                      {/* Left: Enhanced Vector Graph */}
                      <div className="card" style={{ padding: '24px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', gap: '16px', fontSize: '0.82rem' }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#15803D' }} /> Passed
                            </span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#0D9488' }} /> Ready
                            </span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#F1F5F9', border: '1px solid #CBD5E1' }} /> Blocked
                            </span>
                          </div>
                          {selectedNode && (
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                              onClick={() => setSelectedNode(null)}
                            >
                              Reset Focus
                            </button>
                          )}
                        </div>

                        <div style={{ background: '#FFFFFF', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '20px', display: 'flex', justifyContent: 'center', position: 'relative' }}>
                          <svg viewBox="-0.8 -1.7 5.6 3.4" style={{ width: '100%', maxHeight: '500px' }}>
                            <defs>
                              <marker id="arrow-default" viewBox="0 0 10 10" refX="21" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 10 5 L 0 9 z" fill="#CBD5E1" />
                              </marker>
                              <marker id="arrow-upstream" viewBox="0 0 10 10" refX="21" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 10 5 L 0 9 z" fill="#0284C7" />
                              </marker>
                              <marker id="arrow-downstream" viewBox="0 0 10 10" refX="21" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 10 5 L 0 9 z" fill="#0D9488" />
                              </marker>
                            </defs>

                            {/* Edge Lines */}
                            {activeEdges.map((e, idx) => {
                              const p1 = graphData.positions[e.source];
                              const p2 = graphData.positions[e.target];
                              if (!p1 || !p2) return null;

                              const isUpstream = selectedNode ? (e.target === selectedNode) : false;
                              const isDownstream = selectedNode ? (e.source === selectedNode) : false;
                              const isDimmed = selectedNode ? (!isUpstream && !isDownstream) : false;

                              let stroke = '#CBD5E1';
                              let marker = 'url(#arrow-default)';
                              let strokeWidth = '0.035';

                              if (isUpstream) {
                                stroke = '#0284C7';
                                marker = 'url(#arrow-upstream)';
                                strokeWidth = '0.065';
                              } else if (isDownstream) {
                                stroke = '#0D9488';
                                marker = 'url(#arrow-downstream)';
                                strokeWidth = '0.065';
                              } else if (isDimmed) {
                                stroke = '#F1F5F9';
                                strokeWidth = '0.02';
                              }

                              return (
                                <line
                                  key={idx}
                                  x1={p1.x} y1={p1.y}
                                  x2={p2.x} y2={p2.y}
                                  stroke={stroke}
                                  strokeWidth={strokeWidth}
                                  markerEnd={marker}
                                  style={{ transition: 'all 0.2s ease' }}
                                />
                              );
                            })}

                            {/* Node Circles */}
                            {graphData.nodes.map(n => {
                              const pos = graphData.positions[n.id] || { x: 0, y: 0 };
                              const isDone = completed.includes(n.code);
                              const isElig = eligibility?.eligible.some(c => c.code === n.code);
                              const isSelected = selectedNode === n.code;
                              const isPrereqOfSelected = selectedNode ? directPrereqs.includes(n.code) : false;
                              const isDependentOfSelected = selectedNode ? directDependents.includes(n.code) : false;
                              const isFaded = selectedNode ? (!isSelected && !isPrereqOfSelected && !isDependentOfSelected) : false;

                              let fill = '#F8FAFC';
                              let stroke = '#94A3B8';
                              let textFill = '#0F172A';

                              if (isDone) {
                                fill = '#15803D';
                                stroke = '#166534';
                                textFill = '#FFFFFF';
                              } else if (isElig) {
                                fill = '#0D9488';
                                stroke = '#0F766E';
                                textFill = '#FFFFFF';
                              }

                              if (isSelected) {
                                stroke = '#2563EB';
                              }

                              return (
                                <g
                                  key={n.id}
                                  transform={`translate(${pos.x}, ${pos.y})`}
                                  onClick={() => setSelectedNode(n.code)}
                                  style={{ cursor: 'pointer', opacity: isFaded ? 0.35 : 1, transition: 'all 0.2s ease' }}
                                >
                                  {/* Selection Aura */}
                                  {isSelected && (
                                    <circle r="0.42" fill="none" stroke="#38BDF8" strokeWidth="0.05" strokeDasharray="0.08 0.04" />
                                  )}
                                  <circle
                                    r="0.32"
                                    fill={fill}
                                    stroke={stroke}
                                    strokeWidth={isSelected ? '0.06' : '0.035'}
                                  />
                                  <text
                                    textAnchor="middle"
                                    dy="0.08"
                                    fontSize="0.16"
                                    fontWeight="bold"
                                    fill={textFill}
                                    pointerEvents="none"
                                  >
                                    {n.code}
                                  </text>
                                </g>
                              );
                            })}
                          </svg>
                        </div>
                      </div>

                      {/* Right: Selected Course Inspector Card */}
                      <div className="card" style={{ padding: '24px' }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                          Course Inspector
                        </div>
                        {selectedCourse ? (
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--navy-900)' }}>{selectedCourse.code}</h3>
                              <span className={`badge ${completed.includes(selectedCourse.code) ? 'badge-completed' : eligibility?.eligible.some(c => c.code === selectedCourse.code) ? 'badge-eligible' : 'badge-blocked'}`}>
                                {completed.includes(selectedCourse.code) ? 'Passed' : eligibility?.eligible.some(c => c.code === selectedCourse.code) ? 'Eligible' : 'Blocked'}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                              {selectedCourse.name}
                            </div>
                            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '18px' }}>
                              {selectedCourse.credits} Academic Credits
                            </div>

                            <hr style={{ border: 'none', borderTop: '1px solid var(--border-light)', margin: '14px 0' }} />

                            {/* Direct Prerequisites */}
                            <div style={{ marginBottom: '16px' }}>
                              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0369A1', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#0284C7' }} />
                                Required Prerequisites ({directPrereqs.length})
                              </div>
                              {directPrereqs.length === 0 ? (
                                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                  None (Foundational Entry Course)
                                </div>
                              ) : (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                  {directPrereqs.map(p => (
                                    <button
                                      key={p}
                                      onClick={() => setSelectedNode(p)}
                                      className={`badge ${completed.includes(p) ? 'badge-completed' : 'badge-blocked'}`}
                                      style={{ cursor: 'pointer', border: 'none' }}
                                    >
                                      {p} {completed.includes(p) ? '✓' : '✗'}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>

                            {/* Direct Unlockables */}
                            <div style={{ marginBottom: '20px' }}>
                              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--teal-600)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#0D9488' }} />
                                Direct Unlockable Courses ({directDependents.length})
                              </div>
                              {directDependents.length === 0 ? (
                                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                  None (Terminal Degree Capstone)
                                </div>
                              ) : (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                  {directDependents.map(d => (
                                    <button
                                      key={d}
                                      onClick={() => setSelectedNode(d)}
                                      className="badge badge-eligible"
                                      style={{ cursor: 'pointer', border: 'none' }}
                                    >
                                      {d} →
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>

                            <button
                              className={`btn ${completed.includes(selectedCourse.code) ? 'btn-secondary' : 'btn-primary'}`}
                              style={{ width: '100%', justifyContent: 'center' }}
                              onClick={() => toggleCourseCompleted(selectedCourse.code)}
                            >
                              {completed.includes(selectedCourse.code) ? 'Mark as Not Completed' : 'Mark as Completed'}
                            </button>
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>
                            Click any node on the graph to inspect its prerequisite requirements and unlockable courses.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ═════════ 5. SEMESTER PLANNER ═════════ */}
          {currentPage === 'planner' && (
            <div>
              <div className="page-header">
                <div>
                  <div className="page-eyebrow">Academic Roadmapping</div>
                  <h1 className="page-title">Semester Planner</h1>
                  <p className="page-subtitle">
                    Automated credit-constrained scheduling respecting strict prerequisite ordering.
                  </p>
                </div>
              </div>

              <div className="card" style={{ marginBottom: '24px' }}>
                <div className="card-title">
                  <CalendarRange size={20} color="var(--teal-600)" />
                  <span>Planning Constraints</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr) auto', gap: '20px', alignItems: 'flex-end' }}>
                  <div>
                    <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      Max Credits Per Semester
                    </label>
                    <input
                      type="number"
                      min={1} max={30}
                      value={planMaxCredits}
                      onChange={e => setPlanMaxCredits(parseInt(e.target.value) || 12)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontSize: '0.9rem' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      Number of Semesters
                    </label>
                    <input
                      type="number"
                      min={1} max={12}
                      value={planSemesters}
                      onChange={e => setPlanSemesters(parseInt(e.target.value) || 4)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontSize: '0.9rem' }}
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', height: '40px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.88rem', fontWeight: 500 }}>
                      <input
                        type="checkbox"
                        checked={planIncludeCompleted}
                        onChange={e => setPlanIncludeCompleted(e.target.checked)}
                      />
                      <span>Include Completed Courses</span>
                    </label>
                  </div>
                  <div>
                    <button className="btn btn-primary" onClick={handleGeneratePlan} disabled={planningLoading}>
                      {planningLoading ? 'Computing...' : 'Generate Semester Plan'}
                    </button>
                  </div>
                </div>
              </div>

              {planResult && (
                <div>
                  <div style={{ marginBottom: '20px' }}>
                    {planResult.status === 'complete' ? (
                      <div style={{ padding: '16px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 'var(--radius-md)', color: '#166534', fontWeight: 600 }}>
                        ✓ Complete plan generated: All courses successfully scheduled without exceeding {planMaxCredits} credits per semester.
                      </div>
                    ) : planResult.status === 'partial' ? (
                      <div style={{ padding: '16px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 'var(--radius-md)', color: '#B45309', fontWeight: 600 }}>
                        ⚠️ Partial schedule: {planResult.message}
                      </div>
                    ) : (
                      <div style={{ padding: '16px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius-md)', color: '#B91C1C', fontWeight: 600 }}>
                        ❌ Infeasible plan: {planResult.message}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                    {planResult.plan.map((sem, idx) => {
                      const semCourses = sem.map(code => courses.find(c => c.code === code)).filter(Boolean) as Course[];
                      const used = semCourses.reduce((sum, c) => sum + c.credits, 0);
                      const pct = Math.min(100, Math.round((used / planMaxCredits) * 100));

                      return (
                        <div key={idx} className="card">
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--navy-900)' }}>Semester {idx + 1}</span>
                            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: used > planMaxCredits ? 'var(--rose-600)' : 'var(--teal-600)' }}>
                              {used} / {planMaxCredits} Credits
                            </span>
                          </div>

                          <div style={{ width: '100%', height: '6px', background: '#E2E8F0', borderRadius: '999px', overflow: 'hidden', marginBottom: '16px' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: 'var(--teal-600)', borderRadius: '999px' }} />
                          </div>

                          {semCourses.length === 0 ? (
                            <div style={{ color: 'var(--text-subtle)', fontSize: '0.85rem', textAlign: 'center', padding: '16px 0' }}>
                              No courses scheduled
                            </div>
                          ) : (
                            semCourses.map(c => (
                              <div key={c.code} style={{ padding: '10px 12px', background: '#F8FAFC', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', marginBottom: '8px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.88rem' }}>{c.code}</span>
                                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>{c.credits} cr</span>
                                </div>
                                <div style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-main)', marginTop: '2px' }}>{c.name}</div>
                              </div>
                            ))
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ═════════ 6. MATHEMATICS LAB ═════════ */}
          {currentPage === 'math' && (
            <div>
              <div className="page-header">
                <div>
                  <div className="page-eyebrow">Discrete Foundations</div>
                  <h1 className="page-title">Mathematics Lab</h1>
                  <p className="page-subtitle">
                    Explore the formal discrete mathematical proofs, conjunctions, posets, and combinatorics running CurricuLogic.
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-light)', marginBottom: '24px', overflowX: 'auto' }}>
                {[
                  { id: 'logic', label: '1. Propositional Logic' },
                  { id: 'relations', label: '2. Binary Relations' },
                  { id: 'poset', label: '3. Posets & Hasse' },
                  { id: 'toposort', label: '4. Topological Sorting' },
                  { id: 'pigeonhole', label: '5. Pigeonhole Principle' },
                  { id: 'combinatorics', label: '6. Combinatorics' },
                ].map(t => (
                  <button
                    key={t.id}
                    onClick={() => setMathTab(t.id as any)}
                    style={{
                      padding: '10px 16px',
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      color: mathTab === t.id ? 'var(--teal-600)' : 'var(--text-muted)',
                      borderBottom: mathTab === t.id ? '2px solid var(--teal-600)' : '2px solid transparent',
                    }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {mathTab === 'logic' && (
                <div className="card">
                  <div className="card-title">Propositional Conjunction of Prerequisites</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
                    Eligibility is modeled as: <code>eligible(c) ⟺ ⋀_{"{p ∈ prereqs}"} done(p)</code>.
                    Select variables to generate an exact truth table:
                  </p>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                    {['PRG', 'MAT', 'DST', 'DSM', 'OS'].map(v => (
                      <button
                        key={v}
                        className={`btn ${truthVar.includes(v) ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ padding: '4px 10px', fontSize: '0.8rem' }}
                        onClick={() => {
                          setTruthVar(prev => prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v]);
                        }}
                      >
                        {v}
                      </button>
                    ))}
                  </div>

                  <div className="table-wrap" style={{ maxWidth: '480px' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          {truthVar.map(v => <th key={v}>{v}</th>)}
                          <th style={{ background: '#F0FDFA', color: 'var(--teal-600)' }}>Eligible (AND)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {truthTable.map((row, idx) => (
                          <tr key={idx}>
                            {truthVar.map(v => (
                              <td key={v} style={{ fontFamily: 'var(--font-mono)' }}>{row[v]}</td>
                            ))}
                            <td style={{ fontWeight: 700, color: row.Eligible ? '#15803D' : '#94A3B8' }}>
                              {row.Eligible}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {mathTab === 'pigeonhole' && (
                <div className="card">
                  <div className="card-title">Generalized Pigeonhole Capacity Check</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
                    If <code>R</code> credits must be distributed across <code>s</code> semesters, at least one semester must carry <code>⌈R / s⌉</code> credits. If <code>⌈R / s⌉ &gt; k</code>, no valid plan exists.
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', maxWidth: '640px', marginBottom: '20px' }}>
                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Credits to Schedule (R)</label>
                      <input type="number" value={phCredits} onChange={e => setPhCredits(parseInt(e.target.value) || 0)} style={{ width: '100%', padding: '8px' }} />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Max per Semester (k)</label>
                      <input type="number" value={phMax} onChange={e => setPhMax(parseInt(e.target.value) || 12)} style={{ width: '100%', padding: '8px' }} />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Semesters (s)</label>
                      <input type="number" value={phSems} onChange={e => setPhSems(parseInt(e.target.value) || 4)} style={{ width: '100%', padding: '8px' }} />
                    </div>
                  </div>

                  {phCheck && (
                    <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: phCheck.feasible ? '#F0FDF4' : '#FEF2F2', border: `1px solid ${phCheck.feasible ? '#BBF7D0' : '#FECACA'}`, color: phCheck.feasible ? '#166534' : '#B91C1C', fontWeight: 600 }}>
                      ⌈{phCredits} / {phSems}⌉ = {phCheck.min_load} credits vs Limit k = {phMax} credits
                      <br />
                      {phCheck.feasible ? '✓ Feasibility check passed.' : '❌ Mathematically impossible: at least one semester must exceed the credit cap.'}
                    </div>
                  )}
                </div>
              )}

              {mathTab === 'combinatorics' && (
                <div className="card">
                  <div className="card-title">Permutations & Combinations for Elective Selection</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
                    Choosing <code>k</code> courses from <code>n</code> electives without order uses combinations <code>C(n, k) = n! / (k!(n-k)!)</code>.
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', maxWidth: '400px', marginBottom: '20px' }}>
                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Total Items (n)</label>
                      <input type="number" value={combN} onChange={e => setCombN(parseInt(e.target.value) || 0)} style={{ width: '100%', padding: '8px' }} />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Choose (k)</label>
                      <input type="number" value={combK} onChange={e => setCombK(parseInt(e.target.value) || 0)} style={{ width: '100%', padding: '8px' }} />
                    </div>
                  </div>

                  {combResult && (
                    <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: '#F8FAFC', border: '1px solid var(--border-light)' }}>
                      <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--navy-900)' }}>
                        C({combN}, {combK}) = {combResult.combinations.toLocaleString()} combinations
                      </div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-muted)', marginTop: '4px' }}>
                        P({combN}, {combK}) = {combResult.permutations.toLocaleString()} ordered permutations
                      </div>
                    </div>
                  )}
                </div>
              )}

              {mathTab === 'relations' && (
                <div className="card">
                  <div className="card-title">Binary Relations on Course Vertices</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    The prerequisite set is formalized as <code>R ⊆ C × C</code> where <code>(p, c) ∈ R</code> signifies that <code>p</code> is a direct prerequisite of <code>c</code>.
                  </p>
                  <pre style={{ background: '#F8FAFC', padding: '16px', borderRadius: 'var(--radius-md)', marginTop: '16px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                    {graphData?.edges.map(e => `(${e.source}, ${e.target})`).join(', ')}
                  </pre>
                </div>
              )}

              {mathTab === 'poset' && (
                <div className="card">
                  <div className="card-title">Partial Orders & Transitive Reduction</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    A curriculum without cycles forms a Strict Partially Ordered Set (Poset). A Hasse diagram keeps only covering pairs: <code>b covers a ⟺ a &lt; b and ∄ c (a &lt; c &lt; b)</code>.
                  </p>
                  <div style={{ marginTop: '16px', padding: '16px', background: '#F0FDFA', borderRadius: 'var(--radius-md)', color: 'var(--teal-600)', fontWeight: 600 }}>
                    Redundant indirect edges omitted in Hasse reduction: {graphData?.redundant_edges.length || 0}
                  </div>
                </div>
              )}

              {mathTab === 'toposort' && (
                <div className="card">
                  <div className="card-title">Topological Sort on Acyclic Digraph</div>
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    Topological ordering lists all courses such that for every directed edge <code>(u, v)</code>, <code>u</code> appears before <code>v</code>.
                  </p>
                  <div style={{ marginTop: '16px', padding: '16px', background: '#F8FAFC', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                    {courses.map(c => c.code).join(' → ')}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ═════════ 7. ABOUT ═════════ */}
          {currentPage === 'about' && (
            <div>
              <div className="page-header">
                <div>
                  <div className="page-eyebrow">Academic Project</div>
                  <h1 className="page-title">About CurricuLogic</h1>
                  <p className="page-subtitle">
                    Smart Course Prerequisite Planner developed for BAMAT205: Discrete Mathematics and Linear Algebra.
                  </p>
                </div>
              </div>

              <div className="two-col-grid">
                <div className="card">
                  <div className="card-title">Executive Summary</div>
                  <p style={{ fontSize: '0.9rem', lineHeight: 1.6, color: 'var(--text-main)', marginBottom: '16px' }}>
                    CurricuLogic models academic curricula as discrete mathematical structures. It solves the critical bottleneck where students discover unmet prerequisites too late or face impossible credit limits in graduation semesters.
                  </p>
                  <h4 style={{ fontWeight: 700, margin: '16px 0 8px' }}>Core Objectives</h4>
                  <ul style={{ paddingLeft: '20px', fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    <li>Evaluate course readiness using propositional logic conjunctions.</li>
                    <li>Detect and eliminate circular dependencies before scheduling.</li>
                    <li>Generate realistic semester plans respecting credit caps.</li>
                  </ul>
                </div>

                <div className="card">
                  <div className="card-title">Course Information &amp; Documentation</div>
                  <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: '20px' }}>
                    <div><strong>Course:</strong> BAMAT205 — Discrete Mathematics &amp; Linear Algebra</div>
                    <div><strong>Frontend:</strong> React 19, TypeScript, Vite, Modern Design System</div>
                    <div><strong>Backend:</strong> Python 3.13, FastAPI, NetworkX, Matplotlib</div>
                    <div><strong>Tests:</strong> Comprehensive pytest integration suite (21 passed)</div>
                  </div>
                  <a
                    href="/api/docs/pdf"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', textDecoration: 'none' }}
                  >
                    <FileDown size={18} />
                    Download Academic Documentation (PDF)
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ── Modal for Course Add/Edit ── */}
      {isCourseModalOpen && (
        <div className="modal-overlay" onClick={() => setIsCourseModalOpen(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800 }}>
                {editingCourse ? `Edit Course ${editingCourse.code}` : 'Add New Course'}
              </h3>
              <button onClick={() => setIsCourseModalOpen(false)} style={{ color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>

            {formError && (
              <div style={{ padding: '10px 14px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius-sm)', color: '#B91C1C', fontSize: '0.85rem', marginBottom: '16px' }}>
                {formError}
              </div>
            )}

            <form onSubmit={handleSaveCourse}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Course Code</label>
                <input
                  type="text"
                  value={formCode}
                  onChange={e => setFormCode(e.target.value.toUpperCase())}
                  disabled={!!editingCourse}
                  placeholder="e.g. CS101"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-medium)', fontFamily: 'var(--font-mono)' }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Course Title</label>
                <input
                  type="text"
                  value={formName}
                  onChange={e => setFormName(e.target.value)}
                  placeholder="e.g. Data Structures & Algorithms"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-medium)' }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Credits</label>
                <input
                  type="number"
                  min={1} max={10}
                  value={formCredits}
                  onChange={e => setFormCredits(parseInt(e.target.value) || 3)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-medium)' }}
                />
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Prerequisites</label>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', maxHeight: '120px', overflowY: 'auto', border: '1px solid var(--border-light)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                  {courses.filter(c => c.code !== formCode).map(c => {
                    const isSelected = formPrereqs.includes(c.code);
                    return (
                      <button
                        key={c.code}
                        type="button"
                        onClick={() => {
                          setFormPrereqs(prev => prev.includes(c.code) ? prev.filter(x => x !== c.code) : [...prev, c.code]);
                        }}
                        style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '0.78rem',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 600,
                          background: isSelected ? 'var(--teal-600)' : '#F1F5F9',
                          color: isSelected ? '#FFF' : 'var(--text-main)',
                        }}
                      >
                        {c.code}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsCourseModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Course</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal for Delete Confirmation ── */}
      {deletingCourse && (
        <div className="modal-overlay" onClick={() => setDeletingCourse(null)}>
          <div className="modal-card" onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '12px' }}>Confirm Deletion</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '24px' }}>
              Are you sure you want to delete course <strong>{deletingCourse}</strong>? Any dependent prerequisite links will also be safely removed.
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setDeletingCourse(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={() => handleDeleteCourse(deletingCourse)}>Delete Course</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
