"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "@/context/AppContext";
import { api, Source } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Bot,
  Send,
  Trash2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Sparkles,
  Link,
  MessageSquare,
  BookOpen
} from "lucide-react";
import { toast } from "sonner";

interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  followUps?: string[];
  sources?: Source[];
}

export default function ChatPage() {
  const router = useRouter();
  const {
    roadmapId,
    conversationId,
    setConversationId,
    isAuthenticated,
    loadingAuth,
    user,
    logout
  } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputVal, setInputVal] = useState("");
  const [loading, setLoading] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  // Expanded sources state mapping: messageId -> boolean
  const [expandedSources, setExpandedSources] = useState<{ [key: string]: boolean }>({});

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (isMounted && !loadingAuth && !isAuthenticated) {
      router.push("/auth");
    }
  }, [isMounted, isAuthenticated, loadingAuth, router]);

  // Redirect if no active roadmap is set
  useEffect(() => {
    if (isMounted && isAuthenticated && !roadmapId) {
      toast.error("No Active Roadmap", {
        description: "Please generate a roadmap before starting a chat.",
      });
      router.push("/");
    }
  }, [isMounted, isAuthenticated, roadmapId, router]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  if (!isMounted || loadingAuth || (!isAuthenticated && !loadingAuth) || (isAuthenticated && !roadmapId)) {
    return (
      <div className="flex-1 flex justify-center items-center bg-slate-950">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || loading || !roadmapId) return;

    const userMessageText = textToSend.trim();
    setInputVal("");

    // Add user message to UI
    const userMsgId = `user-${Date.now()}`;
    const userMsg: Message = {
      id: userMsgId,
      sender: "user",
      text: userMessageText,
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await api.sendChatMessage({
        roadmap_id: roadmapId,
        message: userMessageText,
        conversation_id: conversationId,
      });

      // Update conversation ID in context
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      // Add AI response to UI
      const aiMsgId = `ai-${Date.now()}`;
      const aiMsg: Message = {
        id: aiMsgId,
        sender: "ai",
        text: response.response,
        followUps: response.follow_up_questions,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      console.error("Error sending message:", err);
      // api.ts automatically displays the error toast
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(inputVal);
  };

  const handleClearChat = () => {
    setMessages([]);
    setConversationId(null);
    toast.info("Conversation Cleared", {
      description: "Starting a fresh session with your AI tutor.",
    });
  };

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  // Safe markdown style renderer
  const formatMessageText = (text: string) => {
    const parts = text.split(/(```[\s\S]*?```|\*\*.*?\*\*|`.*?`|\n)/);
    return parts.map((part, idx) => {
      if (part.startsWith("```") && part.endsWith("```")) {
        const code = part.slice(3, -3).replace(/^[a-zA-Z]+\n/, "");
        return (
          <pre key={idx} className="bg-slate-950 p-3 rounded-md my-2 overflow-x-auto border border-slate-900 text-xs font-mono text-slate-300">
            <code>{code}</code>
          </pre>
        );
      }
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={idx} className="font-bold text-white">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={idx} className="bg-slate-950 px-1.5 py-0.5 rounded text-xs font-mono border border-slate-900 text-pink-400">{part.slice(1, -1)}</code>;
      }
      if (part === "\n") {
        return <br key={idx} />;
      }
      return part;
    });
  };

  const getSourceTypeColor = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes("task")) return "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20";
    if (t.includes("resource")) return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    return "bg-slate-800 text-slate-300 border border-slate-700";
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-950 h-screen overflow-hidden">
      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md px-4 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/roadmap")}
            className="text-slate-400 hover:text-white hover:bg-slate-900"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-sm font-semibold text-white flex items-center gap-1.5">
              <Bot className="h-4 w-4 text-indigo-400" /> AI Study Partner
            </h1>
            <p className="text-[10px] text-emerald-400 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> Active Session
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <Button
            variant="ghost"
            onClick={handleClearChat}
            className="text-slate-500 hover:text-rose-400 hover:bg-rose-950/10 text-xs flex items-center gap-1.5"
          >
            <Trash2 className="h-4 w-4" /> Reset Chat
          </Button>
        )}
      </header>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="py-12 text-center space-y-6 max-w-lg mx-auto">
              <div className="h-16 w-16 mx-auto rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Sparkles className="h-8 w-8" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-bold text-white">Ask your AI Learning Assistant</h3>
                <p className="text-sm text-slate-400 leading-relaxed font-normal">
                  Your assistant has context on your learning roadmap. You can ask for detail explanations, suggested studies, code snippets, or curriculum adjustments.
                </p>
              </div>

              {/* Suggestions */}
              <div className="grid grid-cols-1 gap-2 pt-4">
                <button
                  onClick={() => handleSend("What is the best order to learn the skills listed in my roadmap?")}
                  className="p-3 text-left bg-slate-900/40 border border-slate-800/80 rounded-xl text-slate-300 hover:bg-indigo-950/20 hover:border-indigo-500/30 text-xs font-semibold flex items-center justify-between group transition-all"
                >
                  <span className="flex items-center gap-2"><BookOpen className="h-4 w-4 text-indigo-400" /> "What is the best order to learn these skills?"</span>
                  <Send className="h-3.5 w-3.5 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </button>
                <button
                  onClick={() => handleSend("Can you give me a detailed starting plan for the first module?")}
                  className="p-3 text-left bg-slate-900/40 border border-slate-800/80 rounded-xl text-slate-300 hover:bg-indigo-950/20 hover:border-indigo-500/30 text-xs font-semibold flex items-center justify-between group transition-all"
                >
                  <span className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-indigo-400" /> "Can you give me a starting plan for the first module?"</span>
                  <Send className="h-3.5 w-3.5 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </button>
                <button
                  onClick={() => handleSend("What are some project alternatives that can help me practice SQL?")}
                  className="p-3 text-left bg-slate-900/40 border border-slate-800/80 rounded-xl text-slate-300 hover:bg-indigo-950/20 hover:border-indigo-500/30 text-xs font-semibold flex items-center justify-between group transition-all"
                >
                  <span className="flex items-center gap-2"><MessageSquare className="h-4 w-4 text-indigo-400" /> "How can I practice my skills with additional projects?"</span>
                  <Send className="h-3.5 w-3.5 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </button>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {/* Bot icon for AI messages */}
              {msg.sender === "ai" && (
                <div className="h-8 w-8 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-1">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              {/* Message Bubble Container */}
              <div className={`max-w-[85%] sm:max-w-[75%] space-y-3.5`}>
                <div
                  className={`rounded-2xl p-4 text-sm leading-relaxed border ${
                    msg.sender === "user"
                      ? "bg-indigo-600 border-indigo-500 text-white rounded-tr-none font-normal"
                      : "bg-slate-900 border-slate-800 text-slate-200 rounded-tl-none font-normal"
                  }`}
                >
                  {/* Message content */}
                  <div>{formatMessageText(msg.text)}</div>

                  {/* Sources Citation Section */}
                  {msg.sender === "ai" && msg.sources && msg.sources.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-800/60">
                      <Collapsible
                        open={expandedSources[msg.id]}
                        onOpenChange={() => toggleSources(msg.id)}
                      >
                        <CollapsibleTrigger className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-300 transition-colors cursor-pointer select-none">
                          <span>References ({msg.sources.length})</span>
                          {expandedSources[msg.id] ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )}
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 space-y-2">
                          {msg.sources.map((src, srcIdx) => (
                            <div key={srcIdx} className="p-2.5 bg-slate-950/80 border border-slate-950 rounded-lg space-y-1.5">
                              <div className="flex justify-between items-center text-[10px]">
                                <Badge className={getSourceTypeColor(src.type)}>
                                  {src.type}
                                </Badge>
                                <div className="flex items-center gap-1 text-slate-500 font-semibold">
                                  Relevance:
                                  <span className="text-slate-400">{(src.score * 100).toFixed(0)}%</span>
                                </div>
                              </div>
                              {/* Simple relevance progress bar */}
                              <div className="w-full bg-slate-900 rounded-full h-1">
                                <div
                                  className="bg-indigo-500 h-1 rounded-full"
                                  style={{ width: `${Math.min(src.score * 100, 100)}%` }}
                                />
                              </div>
                              <p className="text-[11px] text-slate-400 font-normal italic leading-relaxed">
                                "{src.content}"
                              </p>
                            </div>
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    </div>
                  )}
                </div>

                {/* Follow up pills (rendered outside bubble for clickability) */}
                {msg.sender === "ai" && msg.followUps && msg.followUps.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pl-2">
                    {msg.followUps.map((question, qIdx) => (
                      <button
                        key={qIdx}
                        onClick={() => handleSend(question)}
                        disabled={loading}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 border border-indigo-500/20 bg-indigo-950/20 hover:bg-indigo-950/40 rounded-full px-3 py-1.5 transition-all text-left duration-250 cursor-pointer disabled:opacity-50"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing Loading Indicator */}
          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="h-8 w-8 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-1">
                <Bot className="h-4 w-4" />
              </div>
              <div className="bg-slate-900 border border-slate-800 text-slate-400 rounded-2xl rounded-tl-none p-4 flex items-center gap-2 text-xs font-semibold">
                <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
                AI is compiling answer...
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </div>

      {/* Input container */}
      <footer className="border-t border-slate-900 bg-slate-950 px-4 py-4 shrink-0">
        <form onSubmit={handleFormSubmit} className="max-w-3xl mx-auto flex gap-2">
          <Input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Type a message or click follow-up questions..."
            disabled={loading}
            className="flex-1 bg-slate-900 border-slate-800 focus-visible:ring-indigo-500 text-slate-100 placeholder:text-slate-500 py-6"
            autoFocus
          />
          <Button
            type="submit"
            disabled={loading || !inputVal.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 text-white py-6 px-6 shadow-lg shadow-indigo-950/40"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </footer>
    </div>
  );
}
