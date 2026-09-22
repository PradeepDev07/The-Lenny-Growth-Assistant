export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SourceCitation {
  id: string;
  source_title: string;
  guest: string;
  url?: string;
  score?: number;
}

export interface ModelTelemetry {
  provider: string;
  model: string;
  latency_ms: number;
  fallback_used: boolean;
  skill?: string;
  refusal?: boolean;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceCitation[];
  model_info?: ModelTelemetry;
  created_at: string;
}

export interface Artifact {
  id: string;
  session_id: string;
  message_id?: string | null;
  type: "markdown" | "html";
  title: string;
  content: string;
  model_info?: ModelTelemetry;
  created_at: string;
}

export interface SessionDetail extends Session {
  messages: Message[];
  user_metadata?: Record<string, any>;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  db: boolean;
  ollama: boolean;
  cloud_llm_configured: boolean;
}

export interface ProviderStatus {
  configured: boolean;
  default_model: string;
}

export interface PublicConfig {
  app_name: string;
  environment: string;
  version: string;
  default_provider: string;
  providers: Record<string, ProviderStatus>;
  task_routing: Record<string, string>;
  cors_origins: string[];
}

export type GenerationMode = "chat" | "essay" | "artifact";
