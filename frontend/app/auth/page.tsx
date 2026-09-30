"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "@/context/AppContext";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, ShieldCheck, Sparkles, Lock, User, KeyRound } from "lucide-react";
import { toast } from "sonner";

export default function AuthPage() {
  const router = useRouter();
  const { isAuthenticated, setIsAuthenticated, setUser, loadingAuth } = useAppContext();

  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    // If user is already logged in, redirect to home page
    if (!loadingAuth && isAuthenticated) {
      router.push("/");
    }
  }, [isAuthenticated, loadingAuth, router]);

  if (loadingAuth) {
    return (
      <div className="flex-1 flex justify-center items-center bg-slate-950 min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const validate = () => {
    const newErrors: { [key: string]: string } = {};
    const trimmedUser = username.trim();

    if (!trimmedUser) {
      newErrors.username = "Username is required.";
    } else if (trimmedUser.length < 3) {
      newErrors.username = "Username must be at least 3 characters.";
    } else if (!/^[a-zA-Z0-9_]+$/.test(trimmedUser)) {
      newErrors.username = "Username can only contain letters, numbers, and underscores.";
    }

    if (!password) {
      newErrors.password = "Password is required.";
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters.";
    }

    if (activeTab === "register") {
      if (password !== confirmPassword) {
        newErrors.confirmPassword = "Passwords do not match.";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    const trimmedUser = username.trim();

    try {
      if (activeTab === "login") {
        const userResponse = await api.login(trimmedUser, password);
        setUser(userResponse);
        setIsAuthenticated(true);
        toast.success(`Welcome back, ${userResponse.username}!`);
        router.push("/");
      } else {
        const userResponse = await api.register(trimmedUser, password);
        setUser(userResponse);
        setIsAuthenticated(true);
        toast.success(`Welcome aboard, ${userResponse.username}!`);
        router.push("/");
      }
    } catch (err: any) {
      console.error("Authentication failed:", err);
      // Error toast is already displayed by fetchAPI in api.ts
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (tab: "login" | "register") => {
    setActiveTab(tab);
    setUsername("");
    setPassword("");
    setConfirmPassword("");
    setErrors({});
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-950/40 via-slate-950 to-slate-950 min-h-screen">
      {/* Background decorations */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[300px] h-[300px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Header */}
      <div className="text-center z-10 max-w-md mb-8 space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-950/20 text-indigo-400 text-sm font-medium backdrop-blur-sm">
          <ShieldCheck className="h-4 w-4 text-emerald-400" /> Secure JWT Session
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">
          AI Learning Assistant
        </h1>
        <p className="text-slate-400 text-sm max-w-xs mx-auto">
          Please log in or register to manage your personal AI roadmaps and chat sessions.
        </p>
      </div>

      {/* Auth Card */}
      <Card className="w-full max-w-md z-10 bg-slate-900/60 border-slate-800/80 backdrop-blur-md shadow-2xl transition-all duration-300 hover:border-slate-700/80">
        <CardHeader className="pb-4">
          {/* Custom Tabs List */}
          <div className="grid grid-cols-2 p-1 bg-slate-950/80 rounded-lg border border-slate-800/60 mb-4">
            <button
              onClick={() => handleTabChange("login")}
              className={`py-2 text-sm font-semibold rounded-md transition-all duration-200 ${
                activeTab === "login"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-950/40"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => handleTabChange("register")}
              className={`py-2 text-sm font-semibold rounded-md transition-all duration-200 ${
                activeTab === "register"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-950/40"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              Create Account
            </button>
          </div>

          <CardTitle className="text-xl font-bold flex items-center gap-2 text-white">
            <Sparkles className="h-5 w-5 text-indigo-400" />
            {activeTab === "login" ? "Welcome Back" : "Register Account"}
          </CardTitle>
          <CardDescription className="text-slate-400 text-xs">
            {activeTab === "login"
              ? "Access your dashboard, resume your studies, and chat with your AI tutor."
              : "Register below to begin generating personalized learning roadmaps."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div className="space-y-1.5">
              <label htmlFor="username" className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                <User className="h-3.5 w-3.5 text-slate-400" /> Username
              </label>
              <Input
                id="username"
                type="text"
                placeholder="enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="bg-slate-950/80 border-slate-800 focus-visible:ring-indigo-500 text-slate-100 placeholder:text-slate-600"
                disabled={loading}
              />
              {errors.username && (
                <p className="text-xs text-rose-400 font-medium">{errors.username}</p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5 text-slate-400" /> Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-slate-950/80 border-slate-800 focus-visible:ring-indigo-500 text-slate-100 placeholder:text-slate-600"
                disabled={loading}
              />
              {errors.password && (
                <p className="text-xs text-rose-400 font-medium">{errors.password}</p>
              )}
            </div>

            {/* Confirm Password (Register Only) */}
            {activeTab === "register" && (
              <div className="space-y-1.5">
                <label htmlFor="confirmPassword" className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <KeyRound className="h-3.5 w-3.5 text-slate-400" /> Confirm Password
                </label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="bg-slate-950/80 border-slate-800 focus-visible:ring-indigo-500 text-slate-100 placeholder:text-slate-600"
                  disabled={loading}
                />
                {errors.confirmPassword && (
                  <p className="text-xs text-rose-400 font-medium">{errors.confirmPassword}</p>
                )}
              </div>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white font-semibold py-5 mt-4 shadow-lg shadow-indigo-950/50 transition-all duration-300 active:scale-[0.98]"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Please wait...
                </>
              ) : activeTab === "login" ? (
                "Log In"
              ) : (
                "Create Account"
              )}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="pt-2 pb-6 flex justify-center border-t border-slate-800/40 bg-slate-950/20">
          <span className="text-[11px] text-slate-500 text-center flex items-center gap-1">
            <Lock className="h-3 w-3" /> Passwords are securely hashed on the server.
          </span>
        </CardFooter>
      </Card>
    </div>
  );
}
