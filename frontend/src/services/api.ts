import type { HealthResponse } from '../types';

export const apiService = {
  async getHealth(): Promise<HealthResponse> {
    const response = await fetch('/api/health', {
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API health check returned status ${response.status}: ${response.statusText}`);
    }

    return response.json();
  },
};
