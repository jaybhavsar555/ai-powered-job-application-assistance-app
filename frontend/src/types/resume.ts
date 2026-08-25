export interface StructuredResumeData {
  summary?: string;
  tailored_bullets?: string[];
  added_keywords?: string[];
  experience?: Array<{
    company?: string;
    title?: string;
    bullets?: string[];
  }>;
  manual_override?: string;
}

export interface ParserChecks {
  has_summary_section?: boolean;
  has_experience_section?: boolean;
  has_skills_section?: boolean;
  has_education_section?: boolean;
  keyword_density?: number;
  keywords_in_summary?: number;
  keywords_in_skills?: number;
  keywords_in_experience?: number;
  formatting_flags?: string[];
  section_score?: number;
  placement_score?: number;
  overall_parser_score?: number;
  warnings?: string[];
  suggestions?: string[];
}

export interface UnifiedAtsPayload {
  score?: number;
  llm_score?: number;
  parser_score?: number;
  matching_skills?: string[];
  missing_skills?: string[];
  recommendation?: string;
  rationale?: string;
  parser_checks?: ParserChecks;
  analysis_mode?: string;
}

export interface TailorResumeRequestBody {
  job_description: string;
  job_url: string;
  base_resume: string;
  approved_skills: string[];
  before_ats_score: number | null;
  current_tailored_text?: string;
}
