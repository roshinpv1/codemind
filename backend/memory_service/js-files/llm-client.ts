/**
 * Comprehensive LLM Client - TypeScript/Next.js equivalent of Python LLM client
 * Supports multiple providers: OpenAI, Anthropic, Gemini, Ollama, Local, Enterprise, Apigee
 */

import { LLMConfig, LLMProvider, LLMResponse, LLMError, LLMCallOptions } from '../types/llm-types';
import { ApigeeTokenManager, EnterpriseTokenManager } from './token-managers';

export class LLMClient {
  private config: LLMConfig;
  private apigeeTokenManager: ApigeeTokenManager | null = null;
  private enterpriseTokenManager: EnterpriseTokenManager | null = null;

  constructor(config: LLMConfig) {
    this.config = {
      temperature: 0.1,
      maxTokens: 4000,
      timeout: 600000, // 10 minutes in milliseconds
      ...config
    };

    // Initialize provider-specific managers
    if (config.provider === LLMProvider.APIGEE) {
      this.apigeeTokenManager = new ApigeeTokenManager();
    } else if (config.provider === LLMProvider.ENTERPRISE) {
      this.enterpriseTokenManager = new EnterpriseTokenManager();
    }
  }

  async callLLM(prompt: string, options?: LLMCallOptions): Promise<string> {
    try {
      const timeout = options?.timeout || this.config.timeout || 600000;
      const temperature = options?.temperature !== undefined ? options.temperature : this.config.temperature;
      const maxTokens = options?.maxTokens !== undefined ? options.maxTokens : this.config.maxTokens;
      
      switch (this.config.provider) {
        case LLMProvider.OPENAI:
          return await this.callOpenAI(prompt, timeout, temperature, maxTokens);
        case LLMProvider.ANTHROPIC:
          return await this.callAnthropic(prompt, timeout, temperature, maxTokens);
        case LLMProvider.GEMINI:
          return await this.callGemini(prompt, timeout, temperature, maxTokens);
        case LLMProvider.OLLAMA:
          return await this.callOllama(prompt, timeout, temperature, maxTokens);
        case LLMProvider.LOCAL:
          return await this.callLocal(prompt, timeout, temperature, maxTokens);
        case LLMProvider.ENTERPRISE:
          return await this.callEnterprise(prompt, timeout, temperature, maxTokens);
        case LLMProvider.APIGEE:
          return await this.callApigee(prompt, timeout, temperature, maxTokens);
        default:
          throw new LLMError(`Unsupported LLM provider: ${this.config.provider}`, this.config.provider);
      }
    } catch (error) {
      if (error instanceof LLMError) {
        throw error;
      }
      
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`⚠️ LLM call failed for provider ${this.config.provider}: ${errorMessage}`);
      throw new LLMError(
        `LLM call failed: ${errorMessage}`,
        this.config.provider,
        undefined,
        error instanceof Error ? error : undefined
      );
    }
  }

  private async callOpenAI(prompt: string, timeout: number, temperature?: number, maxTokens?: number): Promise<string> {
    if (!this.config.apiKey) {
      throw new LLMError('OpenAI API key not provided', LLMProvider.OPENAI);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const baseUrl = this.config.baseUrl || 'https://api.openai.com/v1';
      
      const response = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: this.config.model,
          messages: [{ role: 'user', content: prompt }],
          temperature: temperature !== undefined ? temperature : this.config.temperature,
          max_tokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: { message: 'Unknown error' } }));
        throw new LLMError(
          `OpenAI API error: ${errorData.error?.message || 'Unknown error'}`,
          LLMProvider.OPENAI,
          response.status
        );
      }

      const data = await response.json();
      return data.choices[0].message.content;

    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new LLMError('OpenAI API call timed out', LLMProvider.OPENAI);
      }
      throw error;
    }
  }

  private async callAnthropic(prompt: string, timeout: number, temperature?: number, maxTokens?: number): Promise<string> {
    if (!this.config.apiKey) {
      throw new LLMError('Anthropic API key not provided', LLMProvider.ANTHROPIC);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const baseUrl = this.config.baseUrl || 'https://api.anthropic.com/v1';
      
      const response = await fetch(`${baseUrl}/messages`, {
        method: 'POST',
        headers: {
          'x-api-key': this.config.apiKey,
          'Content-Type': 'application/json',
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify({
          model: this.config.model,
          messages: [{ role: 'user', content: prompt }],
          temperature: temperature !== undefined ? temperature : this.config.temperature,
          max_tokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: { message: 'Unknown error' } }));
        throw new LLMError(
          `Anthropic API error: ${errorData.error?.message || 'Unknown error'}`,
          LLMProvider.ANTHROPIC,
          response.status
        );
      }

      const data = await response.json();
      return data.content[0].text;

    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new LLMError('Anthropic API call timed out', LLMProvider.ANTHROPIC);
      }
      throw error;
    }
  }

  private async callGemini(prompt: string, timeout: number, temperature?: number, maxTokens?: number): Promise<string> {
    if (!this.config.apiKey) {
      throw new LLMError('Gemini API key not provided', LLMProvider.GEMINI);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const baseUrl = this.config.baseUrl || 'https://generativelanguage.googleapis.com/v1beta';
      
      const response = await fetch(
        `${baseUrl}/models/${this.config.model}:generateContent?key=${this.config.apiKey}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
            generationConfig: {
            temperature: temperature !== undefined ? temperature : this.config.temperature,
            maxOutputTokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
            }
          }),
          signal: controller.signal
        }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: { message: 'Unknown error' } }));
        throw new LLMError(
          `Gemini API error: ${errorData.error?.message || 'Unknown error'}`,
          LLMProvider.GEMINI,
          response.status
        );
      }

      const data = await response.json();
      return data.candidates[0].content.parts[0].text;

    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new LLMError('Gemini API call timed out', LLMProvider.GEMINI);
      }
      throw error;
    }
  }

  private async callOllama(prompt: string, timeout: number, temperature?: number, maxTokens?: number): Promise<string> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const baseUrl = this.config.baseUrl || 'http://localhost:11434';
      
      // Check if prompt contains base64 image data
      const isImagePrompt = prompt.includes('Base64 Image Data:');
      let messages;
      
      if (isImagePrompt) {
        // Extract base64 data and text prompt
        const base64Match = prompt.match(/Base64 Image Data: (.+)/);
        const textPrompt = prompt.replace(/Base64 Image Data: .+/, '').trim();
        
        if (base64Match) {
          const base64Data = base64Match[1];
          const imageMimeType = this.detectImageMimeType(base64Data);
          
          messages = [{
            role: 'user',
            content: [
              { type: 'text', text: textPrompt || 'Analyze this architecture diagram and extract all components, connections, and metadata.' },
              { type: 'image_url', image_url: { url: `data:${imageMimeType};base64,${base64Data}` } }
            ]
          }];
        } else {
          // Fallback to text-only if base64 extraction fails
          messages = [{ role: 'user', content: prompt }];
        }
      } else {
        // Standard text-only prompt
        messages = [{ role: 'user', content: prompt }];
      }

      const response = await fetch(`${baseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: this.config.model,
          messages,
          options: {
            temperature: temperature !== undefined ? temperature : this.config.temperature,
            num_predict: maxTokens !== undefined ? maxTokens : this.config.maxTokens
          },
          stream: false
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new LLMError(
          `Ollama API error: ${errorText}`,
          LLMProvider.OLLAMA,
          response.status
        );
      }

      const data = await response.json();
      return data.message.content;

    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new LLMError('Ollama API call timed out', LLMProvider.OLLAMA);
      }
      throw error;
    }
  }

  private detectImageMimeType(base64Data: string): string {
    // Detect image type from base64 data
    if (base64Data.startsWith('/9j/') || base64Data.startsWith('/9j/4AAQ')) {
      return 'image/jpeg';
    } else if (base64Data.startsWith('iVBORw0KGgo')) {
      return 'image/png';
    } else if (base64Data.startsWith('R0lGOD')) {
      return 'image/gif';
    } else if (base64Data.startsWith('UklGR')) {
      return 'image/webp';
    } else if (base64Data.startsWith('PHN2Zy')) {
      return 'image/svg+xml';
    }
    // Default to PNG if unknown
    return 'image/png';
  }

  private async callLocal(prompt: string, timeout: number, temperature?: number, maxTokens?: number): Promise<string> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      if (!this.config.baseUrl) {
        throw new LLMError('Local LLM base URL not provided', LLMProvider.LOCAL);
      }

      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };

      if (this.config.apiKey && this.config.apiKey !== 'not-needed') {
        headers['Authorization'] = `Bearer ${this.config.apiKey}`;
      }

      // Check if prompt contains base64 image data
      const isImagePrompt = prompt.includes('Base64 Image Data:');
      let messages;
      
      if (isImagePrompt) {
        // Extract base64 data and text prompt
        const base64Match = prompt.match(/Base64 Image Data: (.+)/);
        const textPrompt = prompt.replace(/Base64 Image Data: .+/, '').trim();
        
        if (base64Match) {
          const base64Data = base64Match[1];
          const imageMimeType = this.detectImageMimeType(base64Data);
          
          messages = [{
            role: 'user',
            content: [
              { type: 'text', text: textPrompt || 'Analyze this architecture diagram and extract all components, connections, and metadata.' },
              { type: 'image_url', image_url: { url: `data:${imageMimeType};base64,${base64Data}` } }
            ]
          }];
        } else {
          // Fallback to text-only if base64 extraction fails
          messages = [{ role: 'user', content: prompt }];
        }
      } else {
        // Standard text-only prompt
        messages = [{ role: 'user', content: prompt }];
      }

      const response = await fetch(`${this.config.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: this.config.model,
          messages,
          temperature: temperature !== undefined ? temperature : this.config.temperature,
          max_tokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new LLMError(
          `Local LLM API error: ${errorText}`,
          LLMProvider.LOCAL,
          response.status
        );
      }

      const data = await response.json();
      return data.choices[0].message.content;

    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new LLMError('Local LLM API call timed out', LLMProvider.LOCAL);
      }
      throw error;
    }
  }

  private async callEnterprise(prompt: string, timeout: number, temperature?: number, maxTokens?: number): Promise<string> {
    if (!this.enterpriseTokenManager) {
      throw new LLMError('Enterprise token manager not initialized', LLMProvider.ENTERPRISE);
    }

    if (!this.config.baseUrl) {
      throw new LLMError('Enterprise base URL not provided', LLMProvider.ENTERPRISE);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const token = await this.enterpriseTokenManager.getValidToken();

      const headers: Record<string, string> = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      // Add any additional enterprise headers from environment
      const enterpriseHeadersStr = process.env.ENTERPRISE_LLM_HEADERS || '{}';
      try {
        const additionalHeaders = JSON.parse(enterpriseHeadersStr);
        Object.assign(headers, additionalHeaders);
      } catch (e) {
        // Ignore JSON parse errors for headers
      }

      // Check if prompt contains base64 image data
      const isImagePrompt = prompt.includes('Base64 Image Data:');
      let requestBody: any;

      if (isImagePrompt) {
        // Extract base64 image data and text prompt
        const base64Match = prompt.match(/Base64 Image Data: (.+)/);
        const textPrompt = prompt.replace(/Base64 Image Data: .+/, '').trim();
        
        if (base64Match) {
          const base64Data = base64Match[1];
          const imageMimeType = this.detectImageMimeType(base64Data);
          
          // Enterprise providers may support different formats
          // Try OpenAI-compatible format first
          requestBody = {
            model: this.config.model,
            messages: [
              {
                role: 'user',
                content: [
                  { type: 'text', text: textPrompt },
                  { type: 'image_url', image_url: { url: `data:${imageMimeType};base64,${base64Data}` } }
                ]
              }
            ],
            temperature: temperature !== undefined ? temperature : this.config.temperature,
            max_tokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
          };
        } else {
          requestBody = {
            model: this.config.model,
            prompt: textPrompt,
            temperature: temperature !== undefined ? temperature : this.config.temperature,
            max_tokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
          };
        }
      } else {
        requestBody = {
          model: this.config.model,
          prompt: prompt,
          temperature: temperature !== undefined ? temperature : this.config.temperature,
          max_tokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
        };
      }

      const response = await fetch(this.config.baseUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new LLMError(
          `Enterprise LLM request failed: ${response.status} - ${errorText}`,
          LLMProvider.ENTERPRISE,
          response.status
        );
      }

      const data = await response.json();
      // Handle both OpenAI-compatible and custom response formats
      return data.response || data.choices?.[0]?.message?.content || data.content || data.text || '';

    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new LLMError('Enterprise LLM API call timed out', LLMProvider.ENTERPRISE);
      }
      throw error;
    }
  }

  private async callApigee(prompt: string, timeout: number, temperature?: number, maxTokens?: number): Promise<string> {
    if (!this.apigeeTokenManager) {
      throw new LLMError('Apigee token manager not initialized', LLMProvider.APIGEE);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      // Get Apigee token
      const apigeeToken = await this.apigeeTokenManager.getApigeeToken();

      // Enterprise configuration
      const enterpriseBaseUrl = process.env.ENTERPRISE_BASE_URL;
      const wfUseCaseId = process.env.WF_USE_CASE_ID;
      const wfClientId = process.env.WF_CLIENT_ID;
      const wfApiKey = process.env.WF_API_KEY;

      if (!enterpriseBaseUrl || !wfUseCaseId || !wfClientId || !wfApiKey) {
        throw new LLMError('Apigee enterprise configuration incomplete', LLMProvider.APIGEE);
      }

      // Generate UUIDs for request tracking
      const generateUUID = () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          const r = Math.random() * 16 | 0;
          const v = c === 'x' ? r : (r & 0x3 | 0x8);
          return v.toString(16);
        });
      };

      // Check if prompt contains base64 image data
      const isImagePrompt = prompt.includes('Base64 Image Data:');
      let messages: any[];

      if (isImagePrompt) {
        // Extract base64 image data and text prompt
        const base64Match = prompt.match(/Base64 Image Data: (.+)/);
        const textPrompt = prompt.replace(/Base64 Image Data: .+/, '').trim();
        
        if (base64Match) {
          const base64Data = base64Match[1];
          const imageMimeType = this.detectImageMimeType(base64Data);
          
          messages = [
            {
              role: 'user',
              content: [
                { type: 'text', text: textPrompt },
                { type: 'image_url', image_url: { url: `data:${imageMimeType};base64,${base64Data}` } }
              ]
            }
          ];
        } else {
          messages = [{ role: 'user', content: textPrompt }];
        }
      } else {
        messages = [{ role: 'user', content: prompt }];
      }

      const headers = {
        'x-wf-request-date': new Date().toISOString(),
        'Authorization': `Bearer ${apigeeToken}`,
        'x-request-id': generateUUID(),
        'x-correlation-id': generateUUID(),
        'X-WF-client-id': wfClientId,
        'X-WF-api-key': wfApiKey,
        'X-WF-usecase-id': wfUseCaseId,
        'Content-Type': 'application/json'
      };

      const response = await fetch(`${enterpriseBaseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: this.config.model,
          messages: messages,
          temperature: temperature !== undefined ? temperature : this.config.temperature,
          max_tokens: maxTokens !== undefined ? maxTokens : this.config.maxTokens
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new LLMError(
          `Apigee API error: ${response.status} - ${errorText}`,
          LLMProvider.APIGEE,
          response.status
        );
      }

      const data = await response.json();
      return data.choices[0].message.content;

    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new LLMError('Apigee API call timed out', LLMProvider.APIGEE);
      }
      throw error;
    }
  }

  isAvailable(): boolean {
    try {
      switch (this.config.provider) {
        case LLMProvider.OPENAI:
        case LLMProvider.ANTHROPIC:
        case LLMProvider.GEMINI:
          return !!this.config.apiKey;
        
        case LLMProvider.LOCAL:
        case LLMProvider.OLLAMA:
          return !!this.config.baseUrl;
        
        case LLMProvider.ENTERPRISE:
          return !!(this.enterpriseTokenManager && process.env.ENTERPRISE_LLM_TOKEN);
        
        case LLMProvider.APIGEE:
          const requiredVars = [
            'APIGEE_NONPROD_LOGIN_URL', 'APIGEE_CONSUMER_KEY', 'APIGEE_CONSUMER_SECRET',
            'ENTERPRISE_BASE_URL', 'WF_USE_CASE_ID', 'WF_CLIENT_ID', 'WF_API_KEY'
          ];
          return requiredVars.every(varName => !!process.env[varName]);
        
        default:
          return false;
      }
    } catch (error) {
      return false;
    }
  }

  getConfig(): LLMConfig {
    return { ...this.config };
  }
}
