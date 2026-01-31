/**
 * LLM Factory and Utility Functions
 * Creates LLM clients from environment variables with provider auto-detection
 */

import { LLMClient } from './llm-client';
import { LLMConfig, LLMProvider, LLMError } from '../types/llm-types';

export function createLLMClientFromEnv(): LLMClient | null {
  // Check providers in priority order
  const providers: Array<[LLMProvider, string]> = [
    [LLMProvider.OPENAI, 'OPENAI_API_KEY'],
    [LLMProvider.ANTHROPIC, 'ANTHROPIC_API_KEY'],
    [LLMProvider.GEMINI, 'GEMINI_API_KEY'],
    [LLMProvider.APIGEE, 'APIGEE_NONPROD_LOGIN_URL'],
    [LLMProvider.ENTERPRISE, 'ENTERPRISE_LLM_URL'],
    [LLMProvider.LOCAL, 'LOCAL_LLM_URL'],
    [LLMProvider.OLLAMA, 'OLLAMA_HOST']
  ];

  for (const [provider, envVar] of providers) {
    if (process.env[envVar]) {
      try {
        const config = createConfigForProvider(provider);
        const client = new LLMClient(config);
        if (client.isAvailable()) {
          return client;
        }
      } catch (error) {
        console.warn(`Failed to create ${provider} client: ${error instanceof Error ? error.message : 'Unknown error'}`);
        continue;
      }
    }
  }

  return null;
}

export function createConfigForProvider(provider: LLMProvider): LLMConfig {
  switch (provider) {
    case LLMProvider.OPENAI:
      return {
        provider,
        model: process.env.OPENAI_MODEL || 'gpt-4',
        apiKey: process.env.OPENAI_API_KEY,
        baseUrl: process.env.OPENAI_BASE_URL,
        temperature: parseFloat(process.env.OPENAI_TEMPERATURE || '0.1'),
        maxTokens: parseInt(process.env.OPENAI_MAX_TOKENS || '4000'),
        timeout: parseInt(process.env.OPENAI_TIMEOUT || '600000') // Convert to milliseconds
      };

    case LLMProvider.ANTHROPIC:
      return {
        provider,
        model: process.env.ANTHROPIC_MODEL || 'claude-3-sonnet-20240229',
        apiKey: process.env.ANTHROPIC_API_KEY,
        baseUrl: process.env.ANTHROPIC_BASE_URL,
        temperature: parseFloat(process.env.ANTHROPIC_TEMPERATURE || '0.1'),
        maxTokens: parseInt(process.env.ANTHROPIC_MAX_TOKENS || '4000'),
        timeout: parseInt(process.env.ANTHROPIC_TIMEOUT || '600000')
      };

    case LLMProvider.GEMINI:
      return {
        provider,
        model: process.env.GEMINI_MODEL || 'gemini-pro',
        apiKey: process.env.GEMINI_API_KEY,
        baseUrl: process.env.GEMINI_BASE_URL,
        temperature: parseFloat(process.env.GEMINI_TEMPERATURE || '0.1'),
        maxTokens: parseInt(process.env.GEMINI_MAX_TOKENS || '4000'),
        timeout: parseInt(process.env.GEMINI_TIMEOUT || '600000')
      };

    case LLMProvider.LOCAL:
      return {
        provider,
        model: process.env.LOCAL_LLM_MODEL || 'google/gemma-3n-e4b',
        apiKey: process.env.LOCAL_LLM_API_KEY || 'not-needed',
        baseUrl: process.env.LOCAL_LLM_URL || 'http://localhost:1234/v1',
        temperature: parseFloat(process.env.LOCAL_LLM_TEMPERATURE || '0.1'),
        maxTokens: parseInt(process.env.LOCAL_LLM_MAX_TOKENS || '4000'),
        timeout: parseInt(process.env.LOCAL_LLM_TIMEOUT || '600000')
      };

    case LLMProvider.OLLAMA:
      return {
        provider,
        model: process.env.OLLAMA_MODEL || 'llama-3.2-3b-instruct',
        apiKey: undefined,
        baseUrl: process.env.OLLAMA_HOST || 'http://localhost:1234',
        temperature: parseFloat(process.env.OLLAMA_TEMPERATURE || '0.1'),
        maxTokens: parseInt(process.env.OLLAMA_NUM_PREDICT || '4000'),
        timeout: parseInt(process.env.OLLAMA_TIMEOUT || '600000')
      };

    case LLMProvider.ENTERPRISE:
      return {
        provider,
        model: process.env.ENTERPRISE_LLM_MODEL || 'llama-3.2-3b-instruct',
        apiKey: process.env.ENTERPRISE_LLM_API_KEY,
        baseUrl: process.env.ENTERPRISE_LLM_URL,
        temperature: parseFloat(process.env.ENTERPRISE_LLM_TEMPERATURE || '0.1'),
        maxTokens: parseInt(process.env.ENTERPRISE_LLM_MAX_TOKENS || '4000'),
        timeout: parseInt(process.env.ENTERPRISE_LLM_TIMEOUT || '600000')
      };

    case LLMProvider.APIGEE:
      return {
        provider,
        model: process.env.APIGEE_MODEL || 'gpt-4',
        apiKey: process.env.APIGEE_CONSUMER_KEY, // Used for OAuth client credentials
        baseUrl: process.env.ENTERPRISE_BASE_URL, // Apigee enterprise endpoint
        temperature: parseFloat(process.env.APIGEE_TEMPERATURE || '0.1'),
        maxTokens: parseInt(process.env.APIGEE_MAX_TOKENS || '4000'),
        timeout: parseInt(process.env.APIGEE_TIMEOUT || '600000')
      };

    default:
      throw new LLMError(`Unsupported provider: ${provider}`, provider);
  }
}

// Global LLM client instance (singleton)
let globalLLMClient: LLMClient | null = null;

export async function callLLM(
  prompt: string, 
  useCache: boolean = true, 
  timeout?: number
): Promise<string> {
  // Initialize client if not already done
  if (globalLLMClient === null) {
    globalLLMClient = createLLMClientFromEnv();
    if (globalLLMClient === null) {
      throw new LLMError(
        'No LLM provider configured. Please set appropriate environment variables.',
        LLMProvider.LOCAL // Default fallback
      );
    }
  }

  // Call the LLM with options
  const options = { useCache, timeout };
  return await globalLLMClient.callLLM(prompt, options);
}

// Utility function to get available providers
export function getAvailableProviders(): LLMProvider[] {
  const providers: LLMProvider[] = [];
  
  Object.values(LLMProvider).forEach(provider => {
    try {
      const config = createConfigForProvider(provider);
      const client = new LLMClient(config);
      if (client.isAvailable()) {
        providers.push(provider);
      }
    } catch (error) {
      // Provider not available
    }
  });

  return providers;
}

// Utility function to check if a specific provider is available
export function isProviderAvailable(provider: LLMProvider): boolean {
  try {
    const config = createConfigForProvider(provider);
    const client = new LLMClient(config);
    return client.isAvailable();
  } catch (error) {
    return false;
  }
}

// Reset global client (useful for testing or reconfiguration)
export function resetGlobalLLMClient(): void {
  globalLLMClient = null;
}

// Get current global client info
export function getGlobalClientInfo(): { provider: LLMProvider; model: string; available: boolean } | null {
  if (!globalLLMClient) {
    return null;
  }

  const config = globalLLMClient.getConfig();
  return {
    provider: config.provider,
    model: config.model,
    available: globalLLMClient.isAvailable()
  };
}
