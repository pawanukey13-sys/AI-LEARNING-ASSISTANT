"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { api, UserResponse } from "@/lib/api";

interface AppContextType {
  roadmapId: string | null;
  setRoadmapId: (id: string | null) => void;
  conversationId: string | null;
  setConversationId: (id: string | null) => void;
  roadmapData: any | null;
  setRoadmapData: (data: any | null) => void;
  projectRecommendation: any | null;
  setProjectRecommendation: (data: any | null) => void;
  resetState: () => void;
  isAuthenticated: boolean;
  setIsAuthenticated: (val: boolean) => void;
  user: UserResponse | null;
  setUser: (user: UserResponse | null) => void;
  loadingAuth: boolean;
  logout: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [roadmapId, setRoadmapIdState] = useState<string | null>(null);
  const [conversationId, setConversationIdState] = useState<string | null>(null);
  const [roadmapData, setRoadmapDataState] = useState<any | null>(null);
  const [projectRecommendation, setProjectRecommendationState] = useState<any | null>(null);

  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loadingAuth, setLoadingAuth] = useState<boolean>(true);

  // Load from localStorage on mount (safe for Next.js SSR) and verify authentication
  useEffect(() => {
    try {
      const storedRoadmapId = localStorage.getItem("learning_assistant_roadmap_id");
      const storedConvId = localStorage.getItem("learning_assistant_conversation_id");
      const storedRoadmapData = localStorage.getItem("learning_assistant_roadmap_data");
      const storedProject = localStorage.getItem("learning_assistant_project");

      if (storedRoadmapId) setRoadmapIdState(storedRoadmapId);
      if (storedConvId) setConversationIdState(storedConvId);
      if (storedRoadmapData) setRoadmapDataState(JSON.parse(storedRoadmapData));
      if (storedProject) setProjectRecommendationState(JSON.parse(storedProject));
    } catch (e) {
      console.error("Failed to load state from localStorage:", e);
    }

    // Verify session via HTTP-only cookie
    async function checkAuth() {
      try {
        const currentUser = await api.getMe();
        setUser(currentUser);
        setIsAuthenticated(true);
      } catch (e) {
        // Not logged in or invalid session
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoadingAuth(false);
      }
    }
    checkAuth();
  }, []);

  // Setters that sync to localStorage
  const setRoadmapId = (id: string | null) => {
    setRoadmapIdState(id);
    if (id) {
      localStorage.setItem("learning_assistant_roadmap_id", id);
    } else {
      localStorage.removeItem("learning_assistant_roadmap_id");
    }
  };

  const setConversationId = (id: string | null) => {
    setConversationIdState(id);
    if (id) {
      localStorage.setItem("learning_assistant_conversation_id", id);
    } else {
      localStorage.removeItem("learning_assistant_conversation_id");
    }
  };

  const setRoadmapData = (data: any | null) => {
    setRoadmapDataState(data);
    if (data) {
      localStorage.setItem("learning_assistant_roadmap_data", JSON.stringify(data));
    } else {
      localStorage.removeItem("learning_assistant_roadmap_data");
    }
  };

  const setProjectRecommendation = (data: any | null) => {
    setProjectRecommendationState(data);
    if (data) {
      localStorage.setItem("learning_assistant_project", JSON.stringify(data));
    } else {
      localStorage.removeItem("learning_assistant_project");
    }
  };

  const resetState = () => {
    setRoadmapIdState(null);
    setConversationIdState(null);
    setRoadmapDataState(null);
    setProjectRecommendationState(null);
    localStorage.removeItem("learning_assistant_roadmap_id");
    localStorage.removeItem("learning_assistant_conversation_id");
    localStorage.removeItem("learning_assistant_roadmap_data");
    localStorage.removeItem("learning_assistant_project");
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (e) {
      console.error("Logout API failed:", e);
    } finally {
      setUser(null);
      setIsAuthenticated(false);
      resetState();
    }
  };

  return (
    <AppContext.Provider
      value={{
        roadmapId,
        setRoadmapId,
        conversationId,
        setConversationId,
        roadmapData,
        setRoadmapData,
        projectRecommendation,
        setProjectRecommendation,
        resetState,
        isAuthenticated,
        setIsAuthenticated,
        user,
        setUser,
        loadingAuth,
        logout,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
}
