import { toast } from "sonner";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface RoadmapRequest {
  goal_title: string;
  experience: string;
  known_skills: string[];
  learning_style: string;
  weekly_hours: number;
}

export interface Subtask {
  title: string;
  description: string;
  resources: string[];
}

export interface Task {
  title: string;
  estimated_hours: number;
  priority: string;
  subtasks: Subtask[];
}

export interface RoadmapResponse {
  roadmap_id: string;
  estimated_hours: number;
  skills: string[];
  tasks: Task[];
}

export interface ProjectResponse {
  title: string;
  difficulty: string;
  estimated_hours: number;
  tech_stack: string[];
  features: string[];
  why_this_project: string;
  learning_outcomes: string[];
}

export interface ChatRequest {
  roadmap_id: string;
  message: string;
  conversation_id?: string | null;
}

export interface Source {
  content: string;
  type: string;
  score: number;
}

export interface ChatResponse {
  response: string;
  follow_up_questions: string[];
  sources: Source[];
  conversation_id: string;
}

export interface UserResponse {
  id: string;
  username: string;
}

async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  let response: Response;
  try {
    response = await fetch(url, {
      credentials: "include",
      ...options,
      headers,
    });
  } catch (error: any) {
    const msg = "Failed to connect to the backend server. Make sure it is running on http://localhost:8000.";
    toast.error("API Connection Error", {
      description: msg,
      duration: 5000,
    });
    throw error;
  }

  if (!response.ok) {
    let errorMessage = `HTTP error! Status: ${response.status}`;
    const isAuthMe = endpoint === "/auth/me";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((err: any) => err.msg || JSON.stringify(err)).join(", ");
        } else {
          errorMessage = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
        }
      }
    } catch {
      // Fallback
    }
    
    // Don't show toast for 401 Unauthorized (expected when checking auth or not logged in)
    if (response.status !== 401) {
      toast.error("API Error", {
        description: errorMessage,
        duration: 5000,
      });
    }
    throw new Error(errorMessage);
  }

  return await response.json() as T;
}

export const api = {
  generateRoadmap: (data: RoadmapRequest) => {
    return fetchAPI<RoadmapResponse>("/roadmap", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  recommendProject: (roadmapId: string) => {
    return fetchAPI<ProjectResponse>("/project", {
      method: "POST",
      body: JSON.stringify({ roadmap_id: roadmapId }),
    });
  },

  sendChatMessage: (data: ChatRequest) => {
    return fetchAPI<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        roadmap_id: data.roadmap_id,
        message: data.message,
        conversation_id: data.conversation_id || null,
        stream: false,
      }),
    });
  },

  register: (username: string, password: string) => {
    return fetchAPI<UserResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  login: (username: string, password: string) => {
    return fetchAPI<UserResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  logout: () => {
    return fetchAPI<{ message: string }>("/auth/logout", {
      method: "POST",
    });
  },

  getMe: () => {
    return fetchAPI<UserResponse>("/auth/me", {
      method: "GET",
    });
  },
};
