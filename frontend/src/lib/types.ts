// Mirrors backend/research/events.py and schemas.py.

export type SearchQuery = {
  query: string;
  topic: "general" | "news";
  days: number | null;
};

export type SourceSummary = {
  id: number;
  title: string;
  domain: string;
  url: string;
};

export type UnsupportedClaim = {
  claim: string;
  source_id: number | null;
  reason: string;
};

export type Critique = {
  accuracy: number;
  coverage: number;
  citation_quality: number;
  clarity: number;
  recency: number;
  overall: number;
  strengths: string[];
  gaps: string[];
  unsupported_claims: UnsupportedClaim[];
  needs_more_research: boolean;
  followup_queries: string[];
};

export type Draft = {
  version: number;
  report: string;
  critique: Critique | null;
};

export type ResearchEvent =
  | { name: "run"; data: { id: string } }
  | { name: "plan"; data: { queries: SearchQuery[] } }
  | { name: "sources"; data: { added: SourceSummary[]; round: number } }
  | { name: "draft"; data: { version: number; report: string } }
  | { name: "critique"; data: { version: number; critique: Critique } }
  | {
      name: "final";
      data: {
        report: string;
        score: number | null;
        sources: SourceSummary[];
        drafts: Draft[];
        elapsed_s: number;
      };
    }
  | { name: "error"; data: { message: string } };

export type SavedRun = {
  id: string;
  topic: string;
  created_at: string;
  status: "running" | "done" | "error";
  final_report: string | null;
  final_score: number | null;
  drafts: Draft[];
  sources: SourceSummary[];
  queries: SearchQuery[];
  elapsed_s: number | null;
  error: string | null;
};

export const RUBRIC = [
  ["accuracy", "Accuracy"],
  ["coverage", "Coverage"],
  ["citation_quality", "Citations"],
  ["clarity", "Clarity"],
  ["recency", "Recency"],
] as const;
