"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "@/context/AppContext";
import { api, Task } from "@/lib/api";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowLeft,
  Calendar,
  Clock,
  ExternalLink,
  MessageSquare,
  Sparkles,
  Trophy,
  Loader2,
  ListTodo,
  Layers,
  BookOpen
} from "lucide-react";
import { toast } from "sonner";

export default function RoadmapPage() {
  const router = useRouter();
  const {
    roadmapId,
    roadmapData,
    projectRecommendation,
    setProjectRecommendation,
    isAuthenticated,
    loadingAuth,
    user,
    logout
  } = useAppContext();

  const [loadingProject, setLoadingProject] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  // Avoid hydration mismatch
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (isMounted && !loadingAuth && !isAuthenticated) {
      router.push("/auth");
    }
  }, [isMounted, isAuthenticated, loadingAuth, router]);

  // Redirect if no roadmap data or ID is available after mount
  useEffect(() => {
    if (isMounted && isAuthenticated && !roadmapId && !roadmapData) {
      toast.error("No Roadmap Found", {
        description: "Please generate a roadmap first.",
      });
      router.push("/");
    }
  }, [isMounted, isAuthenticated, roadmapId, roadmapData, router]);

  if (!isMounted || loadingAuth || (!isAuthenticated && !loadingAuth) || (isAuthenticated && !roadmapId && !roadmapData)) {
    return (
      <div className="flex-1 flex justify-center items-center bg-slate-950">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  // Use state data or fallback
  const data = roadmapData;
  if (!data) return null;

  const handleSuggestProject = async () => {
    if (!roadmapId) return;
    setLoadingProject(true);
    try {
      const response = await api.recommendProject(roadmapId);
      setProjectRecommendation(response);
      toast.success("Project Recommended!", {
        description: `Suggested project: ${response.title}`,
      });
    } catch (err) {
      console.error("Error recommending project:", err);
    } finally {
      setLoadingProject(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    const p = priority.toLowerCase();
    if (p === "high") return "bg-rose-500/10 border-rose-500/30 text-rose-400";
    if (p === "medium") return "bg-amber-500/10 border-amber-500/30 text-amber-400";
    return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
  };

  const getDifficultyColor = (diff: string) => {
    const d = diff.toLowerCase();
    if (d === "advanced") return "bg-rose-500/10 border-rose-500/30 text-rose-400 border";
    if (d === "intermediate") return "bg-amber-500/10 border-amber-500/30 text-amber-400 border";
    return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 border";
  };

  const getResourceUrl = (res: string) => {
    if (res.startsWith("http://") || res.startsWith("https://")) {
      return res;
    }
    return `https://www.google.com/search?q=${encodeURIComponent(res)}`;
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-950 min-h-screen relative">
      {/* Header bar */}
      <header className="sticky top-0 z-45 w-full border-b border-slate-900 bg-slate-950/80 backdrop-blur-md">
        <div className="container max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Button
            variant="ghost"
            onClick={() => router.push("/")}
            className="text-slate-400 hover:text-white flex items-center gap-2 hover:bg-slate-900"
          >
            <ArrowLeft className="h-4 w-4" /> Create New
          </Button>
          <div className="flex items-center gap-4">
            <div className="text-sm font-semibold tracking-wide text-indigo-400 flex items-center gap-1.5 mr-2">
              <Layers className="h-4 w-4" /> AI LEARNING ASSISTANT
            </div>
            <div className="h-4 w-px bg-slate-800 hidden sm:block" />
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-full border border-slate-800/40">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span>{user?.username}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={logout}
              className="text-xs font-bold border-slate-800 hover:bg-rose-950/15 hover:text-rose-400 text-slate-400"
            >
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 space-y-8 z-10 pb-24">
        {/* Top Header Card */}
        <div className="space-y-4">
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white flex items-center gap-3">
            Your Personalized Learning Journey
          </h1>
          <p className="text-slate-400 text-sm md:text-base font-normal leading-relaxed">
            We have analyzed your skills and structured the ultimate roadmap to achieve your goal.
          </p>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <Card className="bg-slate-900/40 border-slate-800/80 backdrop-blur-sm shadow-md">
              <CardContent className="pt-4 flex items-center gap-4">
                <div className="p-3 bg-indigo-500/10 rounded-lg text-indigo-400">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">Total Duration</p>
                  <p className="text-xl font-bold text-white">{data.estimated_hours} Hours</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900/40 border-slate-800/80 backdrop-blur-sm shadow-md">
              <CardContent className="pt-4 flex items-center gap-4">
                <div className="p-3 bg-indigo-500/10 rounded-lg text-indigo-400">
                  <ListTodo className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">Total Tasks</p>
                  <p className="text-xl font-bold text-white">{data.tasks?.length || 0} Modules</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900/40 border-slate-800/80 backdrop-blur-sm shadow-md">
              <CardContent className="pt-4 flex items-center gap-4">
                <div className="p-3 bg-indigo-500/10 rounded-lg text-indigo-400">
                  <Calendar className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">Target Focus</p>
                  <p className="text-xl font-bold text-white">{data.skills?.length || 0} Key Skills</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Skills Section */}
        <div className="space-y-3">
          <h2 className="text-xs uppercase font-bold tracking-wider text-slate-500">Target Skills Covered</h2>
          <div className="flex flex-wrap gap-2">
            {data.skills?.map((skill: string, idx: number) => (
              <Badge
                key={idx}
                variant="outline"
                className="bg-indigo-950/20 border-indigo-500/30 text-indigo-300 py-1.5 px-3 rounded-full text-xs font-semibold"
              >
                {skill}
              </Badge>
            ))}
          </div>
        </div>

        {/* Tasks Accordion */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-400" /> Learning Path Modules
          </h2>

          <Accordion className="space-y-3 w-full">
            {data.tasks?.map((task: Task, idx: number) => (
              <AccordionItem
                value={`task-${idx}`}
                key={idx}
                className="border border-slate-800 bg-slate-900/40 backdrop-blur-sm rounded-lg px-2"
              >
                <AccordionTrigger className="hover:no-underline py-4 px-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between w-full text-left gap-2">
                    <span className="font-semibold text-slate-200 text-base">{task.title}</span>
                    <div className="flex items-center gap-2.5 mr-4 shrink-0">
                      <Badge className={getPriorityColor(task.priority)} variant="outline">
                        {task.priority} Priority
                      </Badge>
                      <Badge className="bg-slate-800 border-slate-700 text-slate-400 font-normal">
                        {task.estimated_hours} hrs
                      </Badge>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-2 pb-5 border-t border-slate-900/60 pt-4 space-y-4">
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-slate-400">Subtasks & Curriculum:</h4>
                    <div className="grid grid-cols-1 gap-3.5">
                      {task.subtasks?.map((subtask, subIdx) => (
                        <div key={subIdx} className="p-3 bg-slate-950/50 border border-slate-900 rounded-lg space-y-1.5">
                          <div className="flex items-start justify-between">
                            <span className="font-semibold text-slate-200 text-sm">{subtask.title}</span>
                          </div>
                          <p className="text-xs text-slate-400 leading-relaxed font-normal">{subtask.description}</p>
                          {subtask.resources && subtask.resources.length > 0 && (
                            <div className="flex flex-wrap items-center gap-2 pt-1">
                              <span className="text-[10px] text-slate-500 uppercase font-bold">Resources:</span>
                              {subtask.resources.map((res, resIdx) => (
                                <a
                                  key={resIdx}
                                  href={getResourceUrl(res)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
                                >
                                  {res} <ExternalLink className="h-3 w-3" />
                                </a>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>

        {/* Project Suggestion Section */}
        <div className="border-t border-slate-900 pt-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Trophy className="h-5 w-5 text-indigo-400" /> Capstone Project Recommendation
              </h2>
              <p className="text-slate-400 text-xs mt-1 font-normal">
                Put your knowledge to the test by building a hands-on project customized to your roadmap.
              </p>
            </div>
            {!projectRecommendation && (
              <Button
                onClick={handleSuggestProject}
                disabled={loadingProject}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold flex items-center gap-2 shadow-lg shadow-indigo-950/40 transition-all duration-300 shrink-0"
              >
                {loadingProject ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Suggesting...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" /> Recommend a Project
                  </>
                )}
              </Button>
            )}
          </div>

          {/* Project Details Card */}
          {projectRecommendation && (
            <Card className="bg-gradient-to-br from-slate-900 to-indigo-950/20 border-slate-800 overflow-hidden shadow-xl animate-in fade-in zoom-in duration-300">
              <CardHeader className="border-b border-slate-800 bg-slate-900/30">
                <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                  <div>
                    <CardTitle className="text-xl font-bold text-white">{projectRecommendation.title}</CardTitle>
                    <CardDescription className="text-slate-400">Customized Hands-on Project</CardDescription>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge className={getDifficultyColor(projectRecommendation.difficulty)}>
                      {projectRecommendation.difficulty}
                    </Badge>
                    <Badge className="bg-slate-800 border-slate-700 text-slate-300 font-normal">
                      {projectRecommendation.estimated_hours} hrs build time
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="py-6 space-y-6">
                {/* Tech Stack & Why */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2.5">
                    <h4 className="text-xs uppercase font-bold tracking-wider text-slate-500">Tech Stack Required</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {projectRecommendation.tech_stack?.map((tech: string, idx: number) => (
                        <Badge key={idx} variant="secondary" className="bg-slate-800/80 border-slate-700/50 text-slate-200">
                          {tech}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <h4 className="text-xs uppercase font-bold tracking-wider text-slate-500">Why Build This?</h4>
                    <p className="text-sm text-slate-300 leading-relaxed font-normal">{projectRecommendation.why_this_project}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                  {/* Features */}
                  <div className="space-y-2">
                    <h4 className="text-xs uppercase font-bold tracking-wider text-slate-500">Key Features to Implement</h4>
                    <ul className="space-y-1.5">
                      {projectRecommendation.features?.map((feat: string, idx: number) => (
                        <li key={idx} className="text-sm text-slate-300 flex items-start gap-2 font-normal">
                          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 mt-2 shrink-0" />
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Learning Outcomes */}
                  <div className="space-y-2">
                    <h4 className="text-xs uppercase font-bold tracking-wider text-slate-500">Target Learning Outcomes</h4>
                    <ul className="space-y-1.5">
                      {projectRecommendation.learning_outcomes?.map((outcome: string, idx: number) => (
                        <li key={idx} className="text-sm text-slate-300 flex items-start gap-2 font-normal">
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 mt-2 shrink-0" />
                          <span>{outcome}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-800/80 bg-slate-950/40 py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <span className="text-[11px] text-slate-500 font-normal">Ready to build? Ask the AI chat about project architecture and file layouts!</span>
                <Button
                  variant="link"
                  onClick={handleSuggestProject}
                  disabled={loadingProject}
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 p-0 h-auto self-end shrink-0"
                >
                  {loadingProject ? "Loading..." : "Suggest a different project"}
                </Button>
              </CardFooter>
            </Card>
          )}
        </div>
      </main>

      {/* Floating Chat Button */}
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          onClick={() => router.push("/chat")}
          className="h-14 w-14 rounded-full bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white shadow-xl shadow-indigo-950/70 hover:scale-105 active:scale-95 transition-all duration-300 flex items-center justify-center p-0 group"
          title="Chat with AI Tutor"
        >
          <MessageSquare className="h-6 w-6 group-hover:rotate-6 transition-transform" />
          <span className="absolute right-16 scale-0 group-hover:scale-100 bg-slate-900 text-slate-200 border border-slate-800 text-xs font-semibold py-1.5 px-3 rounded-md shadow-lg whitespace-nowrap transition-all duration-200 origin-right">
            Chat with AI Tutor
          </span>
        </Button>
      </div>
    </div>
  );
}
