import type { Course, Metrics, EligibilityResult, GraphData, SemesterPlanResult } from './types';

const API_BASE = '/api';

export const api = {
  async getCourses(): Promise<Course[]> {
    const res = await fetch(`${API_BASE}/courses`);
    if (!res.ok) throw new Error('Failed to load courses');
    return res.json();
  },

  async saveCourses(courses: Course[]): Promise<Course[]> {
    const res = await fetch(`${API_BASE}/courses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(courses),
    });
    if (!res.ok) throw new Error('Failed to save courses');
    return res.json();
  },

  async resetCourses(): Promise<Course[]> {
    const res = await fetch(`${API_BASE}/courses/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset courses');
    return res.json();
  },

  async getMetrics(completed: string[]): Promise<Metrics> {
    const res = await fetch(`${API_BASE}/metrics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(completed),
    });
    if (!res.ok) throw new Error('Failed to fetch metrics');
    return res.json();
  },

  async getEligibility(completed: string[]): Promise<EligibilityResult> {
    const res = await fetch(`${API_BASE}/eligibility`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(completed),
    });
    if (!res.ok) throw new Error('Failed to fetch eligibility');
    return res.json();
  },

  async getGraph(): Promise<GraphData> {
    const res = await fetch(`${API_BASE}/graph`);
    if (!res.ok) throw new Error('Failed to load graph data');
    return res.json();
  },

  async planSemesters(params: {
    max_credits: number;
    semesters: number;
    completed: string[];
    include_completed: boolean;
  }): Promise<SemesterPlanResult> {
    const res = await fetch(`${API_BASE}/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error('Failed to generate plan');
    return res.json();
  },

  async getTruthTable(variables: string[]): Promise<Record<string, number>[]> {
    const res = await fetch(`${API_BASE}/math/truth-table`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ variables }),
    });
    if (!res.ok) throw new Error('Failed to compute truth table');
    return res.json();
  },

  async checkCapacity(params: {
    required_credits: number;
    max_credits: number;
    semesters: number;
  }): Promise<{ required: number; capacity: number; min_load: number; feasible: boolean }> {
    const res = await fetch(`${API_BASE}/math/capacity-check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error('Capacity check failed');
    return res.json();
  },

  async getCombinatorics(n: number, k: number): Promise<{ n: number; k: number; combinations: number; permutations: number }> {
    const res = await fetch(`${API_BASE}/math/combinatorics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ n, k }),
    });
    if (!res.ok) throw new Error('Combinatorics calculation failed');
    return res.json();
  },
};
