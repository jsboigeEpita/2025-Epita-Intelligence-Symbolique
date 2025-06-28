import OpenAI from "openai";
import { llm_backend, llm_system_prompt } from "../constants/llm";

const openai = new OpenAI({
  baseURL: "https://api.openai.com/v1",
  apiKey: llm_backend.model.API_KEY,
  dangerouslyAllowBrowser: true,
});

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
  type: string; // snake_case, e.g. 'slippery_slope'
  confidence: number; // between 0 and 1
  span: [number, number]; // [start_index, end_index]
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

/**
 * Performs a complete analysis of argumentative text
 * @param text The text to analyze
 * @returns Analysis results
 */
export async function analyzeText(text: string): Promise<AnalysisResponse> {
  try {
    const response = await openai.chat.completions.create({
      model: llm_backend.model.name,
      messages: [
        { role: "system", content: llm_system_prompt.analyze },
        { role: "user", content: text },
      ],
    });

    console.log(response.choices[0].message.content);
    return JSON.parse(
      response.choices[0].message.content || "{}"
    ) as AnalysisResponse;
  } catch (error) {
    console.error("Error analyzing text:", error);
    throw error;
  }
}

/**
 * Validates the logical structure of an argument
 * @param text The argument text to validate
 * @returns Validation results
 */
export async function validateArgument(
  text: string
): Promise<ValidationResponse> {
  try {
    const response = await openai.chat.completions.create({
      model: llm_backend.model.name,
      messages: [
        { role: "system", content: llm_system_prompt.validate },
        { role: "user", content: text },
      ],
    });
    console.log(response.choices[0].message.content);
    return JSON.parse(
      response.choices[0].message.content || "{}"
    ) as ValidationResponse;
  } catch (error) {
    console.error("Error validating argument:", error);
    throw error;
  }
}

/**
 * Detects logical fallacies in a text
 * @param text The text to check for fallacies
 * @returns Array of detected fallacies
 */
export async function detectFallacies(text: string): Promise<FallacyResponse> {
  try {
    const response = await openai.chat.completions.create({
      model: llm_backend.model.name,
      messages: [
        { role: "system", content: llm_system_prompt.fallacies },
        { role: "user", content: text },
      ],
    });
    console.log(response.choices[0].message.content);
    return JSON.parse(
      response.choices[0].message.content || "{}"
    ) as FallacyResponse;
  } catch (error) {
    console.error("Error detecting fallacies:", error);
    throw error;
  }
}

/**
 * Sends a message to the chat AI assistant using the latest o3-mini model via OpenRouter
 * @param message The user message to send
 * @returns AI response message
 */
export async function sendChatMessage(message: string): Promise<ChatResponse> {
  try {
    const response = await openai.chat.completions.create({
      model: llm_backend.model.name,
      messages: [
        {
          role: "system",
          content:
            "You are an AI assistant specialized in analyzing arguments. Provide clear, structured, and insightful responses about the logical structure, strengths, and weaknesses of the argument.",
        },
        {
          role: "user",
          content: message,
        },
      ],
    });

    return {
      message:
        response.choices[0].message.content || "No response from OpenIA API.",
      timestamp: new Date(),
    };
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
}

/**
 * Helper function to handle API errors
 * @param error The error object
 * @returns A user-friendly error message
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "An unknown error occurred";
}
