/**
 * API client for the mobile argumentation analysis app.
 *
 * When EXPO_PUBLIC_BACKEND_URL is set, calls go to the FastAPI backend
 * (recommended — leverages the full analysis pipeline).
 * Otherwise, falls back to direct OpenAI calls (original behavior).
 */

import OpenAI from "openai";
import { llm_backend, llm_system_prompt } from "../constants/llm";

// ── Configuration ──

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || "";
const USE_BACKEND = !!BACKEND_URL;

const openai = new OpenAI({
  baseURL: "https://api.openai.com/v1",
  apiKey: llm_backend.model.API_KEY,
  dangerouslyAllowBrowser: true,
});

// ── Types ──

export type Argument = {
  id: string;
  text: string;
  premises: string[];
  conclusion: string;
  structure: "deductive" | "inductive" | "analogical" | "abductive" | "other";
  validity: boolean;
  fallacies: string[];
};

export type AnalysisResponse = {
  text: string;
  arguments: Argument[];
  overall_quality: number;
};

export type FallacyInstance = {
  type: string;
  confidence: number;
  span: [number, number];
  explanation: string;
};

export type FallacyResponse = {
  text: string;
  fallacies: FallacyInstance[];
  execution_time: number;
};

export type ValidationFormalization = {
  type: "propositional" | "predicate" | "other";
  premises: string[];
  conclusion: string;
  rule: string;
};

export type ValidationResponse = {
  valid: boolean;
  formalization: ValidationFormalization;
  explanation: string;
  execution_time: number;
};

export type ChatResponse = {
  message: string;
  timestamp: Date;
};

// ── Backend helpers ──

async function backendFetch<T>(path: string, body: object): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Backend error ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

async function llmCall(systemPrompt: string, userText: string): Promise<string> {
  const response = await openai.chat.completions.create({
    model: llm_backend.model.name,
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userText },
    ],
  });
  return response.choices[0].message.content || "{}";
}

// ── API Functions ──

/**
 * Performs a complete analysis of argumentative text.
 * Uses backend pipeline when available, else direct LLM call.
 */
export async function analyzeText(text: string): Promise<AnalysisResponse> {
  if (USE_BACKEND) {
    return backendFetch<AnalysisResponse>("/api/mobile/analyze", { text });
  }

  try {
    const raw = await llmCall(llm_system_prompt.analyze, text);
    console.log(raw);
    return JSON.parse(raw) as AnalysisResponse;
  } catch (error) {
    console.error("Error analyzing text:", error);
    throw error;
  }
}

/**
 * Validates the logical structure of an argument.
 * Uses backend Toulmin analysis when available.
 */
export async function validateArgument(
  text: string
): Promise<ValidationResponse> {
  if (USE_BACKEND) {
    return backendFetch<ValidationResponse>("/api/mobile/validate", { text });
  }

  try {
    const raw = await llmCall(llm_system_prompt.validate, text);
    console.log(raw);
    return JSON.parse(raw) as ValidationResponse;
  } catch (error) {
    console.error("Error validating argument:", error);
    throw error;
  }
}

/**
 * Detects logical fallacies in a text.
 * Uses backend fallacy detection pipeline when available.
 */
export async function detectFallacies(text: string): Promise<FallacyResponse> {
  if (USE_BACKEND) {
    return backendFetch<FallacyResponse>("/api/mobile/fallacies", { text });
  }

  try {
    const raw = await llmCall(llm_system_prompt.fallacies, text);
    console.log(raw);
    return JSON.parse(raw) as FallacyResponse;
  } catch (error) {
    console.error("Error detecting fallacies:", error);
    throw error;
  }
}

/**
 * Sends a message to the chat AI assistant.
 * Uses backend chat endpoint when available.
 */
export async function sendChatMessage(message: string): Promise<ChatResponse> {
  if (USE_BACKEND) {
    const result = await backendFetch<{ message: string; timestamp: string }>(
      "/api/mobile/chat",
      { message }
    );
    return { message: result.message, timestamp: new Date(result.timestamp) };
  }

  try {
    const response = await openai.chat.completions.create({
      model: llm_backend.model.name,
      messages: [
        {
          role: "system",
          content:
            "You are an AI assistant specialized in analyzing arguments. Provide clear, structured, and insightful responses about the logical structure, strengths, and weaknesses of the argument.",
        },
        { role: "user", content: message },
      ],
    });

    return {
      message:
        response.choices[0].message.content || "No response from OpenAI API.",
      timestamp: new Date(),
    };
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
}

/**
 * Helper function to handle API errors.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "An unknown error occurred";
}
