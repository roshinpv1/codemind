/**
 * Token Management for Enterprise and Apigee LLM Providers
 */

export class ApigeeTokenManager {
  private token: string | null = null;
  private tokenExpiry: Date | null = null;

  async getApigeeToken(): Promise<string> {
    // Check if we have a valid cached token
    if (this.token && this.tokenExpiry && new Date() < this.tokenExpiry) {
      return this.token;
    }

    // Fetch new token using OAuth 2.0 client credentials flow
    const token = await this.fetchApigeeToken();
    
    // Cache the token (assuming 1 hour expiry)
    this.token = token;
    this.tokenExpiry = new Date(Date.now() + 60 * 60 * 1000); // 1 hour

    return this.token;
  }

  private async fetchApigeeToken(): Promise<string> {
    const loginUrl = process.env.APIGEE_NONPROD_LOGIN_URL;
    const consumerKey = process.env.APIGEE_CONSUMER_KEY;
    const consumerSecret = process.env.APIGEE_CONSUMER_SECRET;

    if (!loginUrl || !consumerKey || !consumerSecret) {
      throw new Error('Apigee OAuth credentials not configured. Required: APIGEE_NONPROD_LOGIN_URL, APIGEE_CONSUMER_KEY, APIGEE_CONSUMER_SECRET');
    }

    try {
      // Prepare OAuth 2.0 client credentials request
      const credentials = Buffer.from(`${consumerKey}:${consumerSecret}`).toString('base64');
      process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${credentials}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: 'grant_type=client_credentials'
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new Error(`Apigee OAuth failed: ${response.status} - ${errorText}`);
      }

      const tokenData = await response.json();
      
      if (!tokenData.access_token) {
        throw new Error('No access_token received from Apigee OAuth');
      }

      return tokenData.access_token;

    } catch (error) {
      console.error('Apigee token fetch failed:', error);
      throw new Error(`Failed to fetch Apigee token: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  clearToken(): void {
    this.token = null;
    this.tokenExpiry = null;
  }

  async refreshToken(): Promise<string> {
    // Clear cached token and get fresh one
    this.clearToken();
    return this.getApigeeToken();
  }
}

export class EnterpriseTokenManager {
  private token: string | null = null;
  private tokenExpiry: Date | null = null;

  async getValidToken(): Promise<string> {
    // Check if we have a valid cached token
    if (this.token && this.tokenExpiry && new Date() < this.tokenExpiry) {
      return this.token;
    }

    // Get token from environment or fetch new one
    const token = process.env.ENTERPRISE_LLM_TOKEN;
    if (!token) {
      throw new Error('ENTERPRISE_LLM_TOKEN environment variable not set');
    }

    // Cache the token (assuming 1 hour expiry)
    this.token = token;
    this.tokenExpiry = new Date(Date.now() + 60 * 60 * 1000); // 1 hour

    return this.token;
  }

  clearToken(): void {
    this.token = null;
    this.tokenExpiry = null;
  }

  async refreshToken(): Promise<string> {
    // Clear cached token and get fresh one
    this.clearToken();
    return this.getValidToken();
  }
}
