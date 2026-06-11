const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://verdicta-1.onrender.com";

export interface AskResponse {
  answer: string;
}

export interface AskRequest {
  query: string;
}

// Auth types
export interface AuthResponse {
  access_token: string;
  token_type: string;
}

const TOKEN_STORAGE_KEY = "authToken";

export function saveToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export async function askLegalQuestion(query: string): Promise<AskResponse> {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    const text = await response.text();
    try {
      const errorObj = JSON.parse(text);
      if (errorObj?.detail) {
        throw new Error(
          typeof errorObj.detail === "string"
            ? errorObj.detail
            : JSON.stringify(errorObj.detail)
        );
      }
    } catch (err) {
      if (err instanceof Error && err.message !== text) throw err;
    }
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function registerUser(username: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      text || `Registration failed with status ${response.status}`
    );
  }

  return response.json();
}

export async function login(
  username: string,
  password: string
): Promise<AuthResponse> {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  // OAuth2PasswordRequestForm accepts optional fields; leave scope/others empty.

  const response = await fetch(`${API_BASE_URL}/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: form.toString(),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Login failed with status ${response.status}`);
  }

  return response.json();
}

export async function verifyToken(token: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/verify-token/${token}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      text || `Token verification failed with status ${response.status}`
    );
  }
  return response.json();
}
