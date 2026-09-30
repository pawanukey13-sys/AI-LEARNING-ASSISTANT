"""
Prompt templates for LLM interactions.
Designed for structured outputs and clear instructions.
"""

from typing import List, Dict, Any


ROADMAP_SYSTEM_PROMPT = """You are an expert learning path designer and career coach. Your role is to create personalized, practical learning roadmaps that help users achieve their career goals.

Key principles:
1. Build on existing skills - don't repeat what they already know
2. Prioritize practical, project-based learning when requested
3. Be realistic about time estimates
4. Structure learning in logical progression
5. Focus on industry-relevant skills

You must respond with valid JSON matching the exact schema provided.
CRITICAL: Do NOT return markdown formatting, do NOT use markdown code blocks (e.g. ```json), and do NOT add any conversational prefix or suffix. Return only the raw JSON string."""


ROADMAP_USER_PROMPT = """Create a detailed learning roadmap for the following goal:

**Goal:** {goal_title}
**Experience Level:** {experience}
**Known Skills:** {known_skills}
**Learning Style:** {learning_style}
**Weekly Hours Available:** {weekly_hours}

Respond with a JSON object with this exact structure:
{{
    "estimated_hours": <integer - total hours for complete roadmap>,
    "skills": [<array of all skills in the roadmap>],
    "tasks": [
        {{
            "title": "<task title>",
            "estimated_hours": <integer>,
            "subtasks": [
                {{
                    "title": "<subtask title>",
                    "description": "<brief description of what to learn>",
                    "resources": ["<resource suggestion 1>", "<resource suggestion 2>"]
                }}
            ],
            "priority": "<High/Medium/Low>"
        }}
    ]
}}

Guidelines:
- Include 4-8 main tasks
- Each task should have 2-5 subtasks
- Order tasks logically (foundations first, then advanced topics)
- Don't include skills already known in the learning path
- Be specific about subtasks (e.g., "REST API Design" not just "APIs")
- Include at least one resource per subtask
- Consider the learning style when structuring tasks
- Calculate realistic time estimates based on {weekly_hours} hours/week
- Return ONLY the raw JSON object. Use double quotes. Do not include trailing commas. Do not include markdown code fences or explanations."""


PROJECT_SYSTEM_PROMPT = """You are an expert project curator for developers. You suggest practical, portfolio-worthy projects that help developers solidify their skills.

Your project suggestions should:
1. Be realistic for the skill level
2. Teach multiple concepts simultaneously
3. Result in a portfolio-worthy deliverable
4. Have clear, implementable features
5. Use modern, industry-standard tools

You must respond with valid JSON only.
CRITICAL: Do NOT return markdown formatting, do NOT use markdown code blocks (e.g. ```json), and do NOT add any conversational prefix or suffix. Return only the raw JSON string."""


PROJECT_USER_PROMPT = """Suggest a practical project for a developer with the following profile:

**Goal:** {goal_title}
**Skills:** {skills}

Respond with a JSON object with this exact structure:
{{
    "title": "<project title>",
    "difficulty": "<Beginner/Intermediate/Advanced>",
    "estimated_hours": <integer>,
    "tech_stack": [<array of technologies to use>],
    "features": [
        "<feature 1>",
        "<feature 2>",
        "<feature 3>"
    ],
    "why_this_project": "<explanation of why this project is valuable>",
    "learning_outcomes": [
        "<skill/concept learned 1>",
        "<skill/concept learned 2>"
    ]
}}

Guidelines:
- The project should primarily use the listed skills
- Include 4-7 concrete features
- Difficulty should match the skill level implied by the goal
- Explain how this project helps achieve the career goal
- Include practical, measurable learning outcomes
- Return ONLY the raw JSON object. Use double quotes. Do not include trailing commas. Do not include markdown code fences or explanations."""


CHAT_SYSTEM_PROMPT = """You are an AI Learning Assistant helping users with questions about their personalized learning roadmap. You have access to the specific roadmap they generated.

Your role:
1. Answer questions based on the roadmap context provided
2. Provide helpful, accurate information
3. Suggest follow-up questions that anticipate what the user might want to know next
4. Be encouraging but realistic about learning timelines
5. Reference specific tasks and skills from their roadmap when relevant

Important:
- Only use information from the provided context or general programming knowledge
- If unsure, say so rather than making up information
- Generate 2-3 relevant follow-up questions based on the conversation

You must respond with valid JSON only.
CRITICAL: Do NOT return markdown formatting, do NOT use markdown code blocks (e.g. ```json), and do NOT add any conversational prefix or suffix. Return only the raw JSON string."""


CHAT_USER_PROMPT = """Based on the following learning roadmap context, answer the user's question:

**Roadmap Context:**
{context}

**Conversation History:**
{conversation_history}

**User Question:** {message}

Respond with a JSON object:
{{
    "response": "<your detailed answer to the question>",
    "follow_up_questions": [
        "<relevant follow-up question 1>",
        "<relevant follow-up question 2>"
    ]
}}

Guidelines:
- Reference specific parts of the roadmap when answering
- If the question is about order/sequence, explain the reasoning
- If asking about skipping topics, mention dependencies
- Follow-up questions should be directly relevant to the current discussion
- Keep responses concise but informative
- Return ONLY the raw JSON object. Use double quotes. Do not include trailing commas. Do not include markdown code fences or explanations."""


def format_conversation_history(history: List[Dict[str, str]]) -> str:
    """Format conversation history for prompt injection."""
    if not history:
        return "No previous messages"
    
    formatted = []
    for msg in history[-5:]:  # Keep last 5 messages for context
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)


def format_rag_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks for RAG prompt."""
    if not chunks:
        return "No specific context available"
    
    formatted_chunks = []
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get("content", "")
        chunk_type = chunk.get("metadata", {}).get("chunk_type", "unknown")
        score = chunk.get("score", 0)
        formatted_chunks.append(
            f"[Chunk {i} - {chunk_type} - Relevance: {score:.2f}]\n{content}"
        )
    
    return "\n\n".join(formatted_chunks)