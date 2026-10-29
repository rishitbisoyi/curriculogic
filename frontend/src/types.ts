export interface Course {
  code: string;
  name: string;
  credits: number;
  prereqs: string[];
}

export interface Metrics {
  total: number;
  completed: number;
  eligible: number;
  blocked: number;
  total_credits: number;
  completed_credits: number;
  remaining_credits: number;
}

export interface EligibilityResult {
  completed: Course[];
  eligible: Course[];
  blocked: (Course & { missing_prereqs: string[] })[];
  has_cycle: boolean;
  cycle_path: string[] | null;
}

export interface GraphNode {
  id: string;
  code: string;
  name: string;
  credits: number;
  prereqs: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  hasse_edges: GraphEdge[];
  redundant_edges: GraphEdge[];
  positions: Record<string, { x: number; y: number }>;
  has_cycle: boolean;
  cycle_path: string[] | null;
}

export interface SemesterPlanResult {
  status: 'complete' | 'partial' | 'infeasible';
  message: string;
  plan: string[][];
  unscheduled: Record<string, string>;
}
