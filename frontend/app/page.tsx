"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "@/context/AppContext";
import { api, RoadmapRequest } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Loader2, Sparkles, BookOpen, Clock, Lightbulb } from "lucide-react";
import { toast } from "sonner";

export default function HomePage() {
  const router = useRouter();
  const {
    setRoadmapId,
    setRoadmapData,
    setProjectRecommendation,
    isAuthenticated,
    loadingAuth,
    user,
    logout
  } = useAppContext();
  
  // Form states and other hooks declared unconditionally at the top
  const [loading, setLoading] = useState(false);
  const [goalTitle, setGoalTitle] = useState("");
  const [experience, setExperience] = useState("");
  const [knownSkillsRaw, setKnownSkillsRaw] = useState("");
  const [learningStyle, setLearningStyle] = useState("");
  const [weeklyHours, setWeeklyHours] = useState<number>(10);
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loadingAuth && !isAuthenticated) {
      router.push("/auth");
    }
  }, [isAuthenticated, loadingAuth, router]);

  // While checking auth, show loading spinner
  if (loadingAuth) {
    return (
      <div className="flex-1 flex justify-center items-center bg-slate-950 min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  // If not authenticated, don't render page content
  if (!isAuthenticated) {
    return null;
  }

  // Skill badge preview helpers
  const getSkillsArray = (raw: string) => {
    return raw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  };

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {};

    if (!goalTitle.trim()) {
      newErrors.goalTitle = "Goal title is required.";
    } else if (!/^[a-zA-Z\s\-]+$/.test(goalTitle.trim())) {
      newErrors.goalTitle = "Goal title can only contain letters, spaces, and hyphens.";
    }

    if (!experience) {
      newErrors.experience = "Please select your experience level.";
    }

    const skills = getSkillsArray(knownSkillsRaw);
    if (skills.length === 0) {
      newErrors.knownSkills = "Please enter at least one skill.";
    }

    if (!learningStyle) {
      newErrors.learningStyle = "Please select a learning style.";
    }

    if (!weeklyHours || weeklyHours < 1 || weeklyHours > 80) {
      newErrors.weeklyHours = "Weekly hours must be between 1 and 80.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    const skills = getSkillsArray(knownSkillsRaw);

    const payload: RoadmapRequest = {
      goal_title: goalTitle.trim(),
      experience,
      known_skills: skills,
      learning_style: learningStyle,
      weekly_hours: Number(weeklyHours),
    };

    try {
      const response = await api.generateRoadmap(payload);
      
      // Save state to context
      setRoadmapId(response.roadmap_id);
      setRoadmapData(response);
      // Reset project recommendation when a new roadmap is generated
      setProjectRecommendation(null);

      toast.success("Roadmap Generated!", {
        description: `Successfully created a roadmap for ${response.skills.length} skills.`,
      });

      router.push("/roadmap");
    } catch (err) {
      // API client fetcher automatically shows toast on network/http error
      console.error("Error generating roadmap:", err);
    } finally {
      setLoading(false);
    }
  };

  const skillsPreview = getSkillsArray(knownSkillsRaw);

  return (
    <div className="flex-1 flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-950/40 via-slate-950 to-slate-950">
      {/* User profile header */}
      <div className="absolute top-6 right-6 z-20 flex items-center gap-3 bg-slate-900/60 border border-slate-800/80 px-4 py-2 rounded-full backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-400" />
          <span className="text-xs font-semibold text-slate-300">Logged in as <strong className="text-white font-bold">{user?.username}</strong></span>
        </div>
        <div className="h-3 w-px bg-slate-800" />
        <button
          onClick={logout}
          className="text-xs font-bold text-rose-400 hover:text-rose-300 transition-colors cursor-pointer select-none"
        >
          Sign Out
        </button>
      </div>

      {/* Background glowing decorations */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[300px] h-[300px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Hero Section */}
      <div className="text-center z-10 max-w-2xl mb-8 space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-950/20 text-indigo-400 text-sm font-medium mb-3 backdrop-blur-sm animate-pulse">
          <Sparkles className="h-4 w-4" /> Powered by RAG & Local LLM
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">
          AI Learning Assistant
        </h1>
        <p className="text-slate-400 text-lg md:text-xl font-normal max-w-xl mx-auto">
          Generate custom learning roadmaps, recommend projects, and chat with your personal AI tutor.
        </p>
      </div>

      {/* Main Form Card */}
      <Card className="w-full max-w-xl z-10 bg-slate-900/60 border-slate-800/80 backdrop-blur-md shadow-2xl transition-all duration-300 hover:border-slate-700/80">
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2 text-white">
            <BookOpen className="h-5 w-5 text-indigo-400" /> Roadmap Generator
          </CardTitle>
          <CardDescription className="text-slate-400">
            Tell us about your learning goals and we will structure a step-by-step path for you.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Goal Title */}
            <div className="space-y-2">
              <label htmlFor="goalTitle" className="text-sm font-medium text-slate-300">
                What role or goal are you aiming for?
              </label>
              <Input
                id="goalTitle"
                placeholder="e.g. Backend Developer"
                value={goalTitle}
                onChange={(e) => setGoalTitle(e.target.value)}
                className="bg-slate-950/80 border-slate-800 focus-visible:ring-indigo-500 text-slate-100 placeholder:text-slate-500"
                disabled={loading}
              />
              {errors.goalTitle ? (
                <p className="text-xs text-rose-400 font-medium">{errors.goalTitle}</p>
              ) : (
                <p className="text-[11px] text-slate-500 font-normal">Only letters, spaces, and hyphens (e.g. Backend Developer, ML Engineer).</p>
              )}
            </div>

            {/* Experience & Weekly Hours Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Experience */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Experience Level</label>
                <Select value={experience} onValueChange={(val) => setExperience(val || "")} disabled={loading}>
                  <SelectTrigger className="bg-slate-950/80 border-slate-800 focus:ring-indigo-500 text-slate-100">
                    <SelectValue placeholder="Select experience" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-800 text-slate-100">
                    <SelectItem value="Less than 1 year">Less than 1 year</SelectItem>
                    <SelectItem value="1-3 years">1-3 years</SelectItem>
                    <SelectItem value="3-5 years">3-5 years</SelectItem>
                    <SelectItem value="5+ years">5+ years</SelectItem>
                  </SelectContent>
                </Select>
                {errors.experience && <p className="text-xs text-rose-400 font-medium">{errors.experience}</p>}
              </div>

              {/* Weekly Hours */}
              <div className="space-y-2">
                <label htmlFor="weeklyHours" className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
                  <Clock className="h-4 w-4 text-slate-400" /> Weekly Commited Hours
                </label>
                <Input
                  id="weeklyHours"
                  type="number"
                  min={1}
                  max={80}
                  value={weeklyHours}
                  onChange={(e) => setWeeklyHours(Number(e.target.value))}
                  className="bg-slate-950/80 border-slate-800 focus-visible:ring-indigo-500 text-slate-100"
                  disabled={loading}
                />
                {errors.weeklyHours ? (
                  <p className="text-xs text-rose-400 font-medium">{errors.weeklyHours}</p>
                ) : (
                  <p className="text-[11px] text-slate-500 font-normal">Number between 1 and 80.</p>
                )}
              </div>
            </div>

            {/* Learning Style */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
                <Lightbulb className="h-4 w-4 text-slate-400" /> Preferred Learning Style
              </label>
              <Select value={learningStyle} onValueChange={(val) => setLearningStyle(val || "")} disabled={loading}>
                <SelectTrigger className="bg-slate-950/80 border-slate-800 focus:ring-indigo-500 text-slate-100">
                  <SelectValue placeholder="Select style" />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800 text-slate-100">
                  <SelectItem value="Project Based">Project Based (Hands-on experiments)</SelectItem>
                  <SelectItem value="Theory First">Theory First (Documentation, books)</SelectItem>
                  <SelectItem value="Hybrid">Hybrid (Mix of theory and projects)</SelectItem>
                  <SelectItem value="Video Tutorials">Video Tutorials (Guided courses)</SelectItem>
                </SelectContent>
              </Select>
              {errors.learningStyle && <p className="text-xs text-rose-400 font-medium">{errors.learningStyle}</p>}
            </div>

            {/* Known Skills */}
            <div className="space-y-2">
              <label htmlFor="knownSkills" className="text-sm font-medium text-slate-300">
                Skills you already know
              </label>
              <Input
                id="knownSkills"
                placeholder="e.g. HTML, CSS, JavaScript (comma separated)"
                value={knownSkillsRaw}
                onChange={(e) => setKnownSkillsRaw(e.target.value)}
                className="bg-slate-950/80 border-slate-800 focus-visible:ring-indigo-500 text-slate-100 placeholder:text-slate-500"
                disabled={loading}
              />
              {errors.knownSkills && <p className="text-xs text-rose-400 font-medium">{errors.knownSkills}</p>}

              {/* Real-time preview */}
              {skillsPreview.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1.5">
                  <span className="text-xs text-slate-400 self-center mr-1">Preview:</span>
                  {skillsPreview.map((skill, idx) => (
                    <Badge key={idx} variant="secondary" className="bg-indigo-950/40 border-indigo-900/50 text-indigo-300 hover:bg-indigo-950/40">
                      {skill}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white font-semibold py-6 mt-4 shadow-lg shadow-indigo-950/50 transition-all duration-300 active:scale-[0.98]"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  Generating Roadmap...
                </>
              ) : (
                <>
                  <Sparkles className="h-5 w-5 mr-2" />
                  Generate My Learning Roadmap
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
