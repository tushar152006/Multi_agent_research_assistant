export type QueryType =
  | "simple_search"
  | "deep_analysis"
  | "critical_review"
  | "startup_idea";

export type SessionSummary = {
  session_id: string;
  query: string;
  query_type: QueryType;
  generated_at: string;
};

export type AgentExecution = {
  agent_name: string;
  status: string;
  detail: string;
};

export type PaperSummary = {
  title: string;
  authors: string[];
  source: string;
  external_id: string;
  abstract: string;
  relevance_score: number;
};

export type ReaderResponse = {
  title: string;
  problem: string;
  methodology: {
    approach: string;
    datasets: string[];
    metrics: string[];
  };
  results: {
    primary_findings: string[];
    metrics: Record<string, string>;
  };
  limitations: string[];
  future_work: string[];
  extracted_sections: Record<string, string>;
};

export type AnalystResponse = {
  query: string;
  themes: string[];
  innovations: Array<{
    paper_title: string;
    innovation: string;
    impact: string;
  }>;
  consensus: string[];
  conflicts: Array<{
    topic: string;
    description: string;
    papers: string[];
  }>;
  gaps: string[];
  practical_applications: string[];
};

export type CriticResponse = {
  query: string;
  critiques: Array<{
    category: string;
    issue: string;
    severity: string;
    evidence: string;
    impact: string;
  }>;
  overall_confidence: number;
  review_mode: string;
  llm_summary: string | null;
};

export type BuilderResponse = {
  query: string;
  project_idea: string;
  value_proposition: string;
  architecture: {
    summary: string;
    components: string[];
    data_flow: string[];
  };
  data_requirements: {
    datasets: string[];
    collection_strategy: string[];
    privacy_considerations: string[];
  };
  mvp_roadmap: Array<{
    name: string;
    duration: string;
    goals: string[];
  }>;
  challenges: Array<{
    challenge: string;
    mitigation: string;
  }>;
};

export type ResearchResponse = {
  query: string;
  query_type: QueryType;
  summary: string;
  papers: PaperSummary[];
  reader_outputs: ReaderResponse[];
  analysis: AnalystResponse | null;
  critique: CriticResponse | null;
  implementation_plan: BuilderResponse | null;
  session_id: string | null;
  execution_trace: AgentExecution[];
  generated_at: string;
};

export type SessionListResponse = {
  sessions: SessionSummary[];
};
