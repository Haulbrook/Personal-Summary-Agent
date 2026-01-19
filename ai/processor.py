"""
AI Processor - Generate summaries, extract tasks, provide insights
"""
import json
from openai import OpenAI
from config import OPENAI_API_KEY, AI_MODEL, TEMPERATURE


class AIProcessor:
    """Handles all AI-powered analysis"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = AI_MODEL

    def _call(self, system: str, user: str, json_mode: bool = False, temperature: float = None) -> str:
        """Make API call to OpenAI"""
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temperature or TEMPERATURE
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def generate_daily_summary(self, content: str) -> str:
        """Generate a concise daily summary"""
        system = """You are a personal journal assistant creating a daily summary.

Your summary should:
- Be 3-5 sentences
- Capture the essence of the day
- Mention key activities, accomplishments, or events
- Note the overall tone/mood if apparent
- Be written in second person ("You...")
- Be warm and insightful, not generic

Focus on what matters. Skip the fluff."""

        return self._call(system, f"Today's journal entries:\n\n{content}")

    def extract_tasks(self, content: str) -> dict:
        """Extract tasks mentioned in the content"""
        system = """You are a task extraction assistant.

Analyze the journal content and identify all tasks/to-dos mentioned.

Categorize them:
- completed: Tasks that were finished, done, completed
- pending: Tasks still needing to be done
- ideas: Things mentioned as "maybe" or "should consider"

Rules:
- Be specific - convert vague mentions into actionable items
- Include deadlines if mentioned
- Don't invent tasks not mentioned

Return JSON:
{
    "completed": [
        {"task": "description", "context": "brief context if relevant"}
    ],
    "pending": [
        {"task": "description", "priority": "high/medium/low", "deadline": "if mentioned or null"}
    ],
    "ideas": [
        {"task": "description", "notes": "any relevant notes"}
    ]
}"""

        result = self._call(system, content, json_mode=True)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"completed": [], "pending": [], "ideas": []}

    def extract_insights(self, content: str) -> dict:
        """Extract mood, energy, themes, and patterns"""
        system = """Analyze this journal entry and extract insights.

Return JSON:
{
    "mood": {
        "primary": "one word (happy, stressed, calm, anxious, excited, tired, motivated, etc.)",
        "secondary": "optional secondary mood or null",
        "confidence": "high/medium/low"
    },
    "energy_level": "1-10 scale based on content",
    "themes": ["theme1", "theme2", "theme3"],
    "wins": ["positive things, accomplishments, good moments"],
    "challenges": ["difficulties, frustrations, obstacles"],
    "people_mentioned": ["names of people mentioned"],
    "notable_quotes": ["any memorable phrases or thoughts worth saving"]
}

Base this ONLY on what's actually written. Don't assume or invent."""

        result = self._call(system, content, json_mode=True)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "mood": {"primary": "unknown", "confidence": "low"},
                "energy_level": 5,
                "themes": [],
                "wins": [],
                "challenges": [],
                "people_mentioned": [],
                "notable_quotes": []
            }

    def suggest_tasks(self, today_content: str, pending_tasks: list, recent_history: list = None) -> list:
        """Generate intelligent task suggestions for tomorrow"""
        pending_str = ""
        if pending_tasks:
            pending_str = "\n\nCURRENT PENDING TASKS:\n"
            pending_str += "\n".join([f"- {t}" for t in pending_tasks])

        history_str = ""
        if recent_history:
            history_str = "\n\nRECENT PATTERNS (last 7 days):\n"
            for entry in recent_history[-7:]:
                history_str += f"- {entry.get('date')}: {entry.get('summary', '')[:100]}...\n"

        system = """You are a proactive personal assistant helping plan tomorrow.

Based on:
1. Today's journal content
2. Pending tasks
3. Recent patterns

Suggest 3-5 actionable tasks for tomorrow.

Your suggestions should:
- Be specific and achievable
- Help complete important pending items
- Consider patterns and recurring needs
- Include a mix of urgent and important
- Be realistic for one day

Return JSON:
{
    "suggestions": [
        {
            "task": "Specific, actionable task description",
            "priority": "high/medium/low",
            "reason": "Why this is suggested (1 sentence)",
            "estimated_time": "rough time estimate",
            "category": "work/personal/health/admin/creative/social"
        }
    ]
}"""

        user = f"""TODAY'S JOURNAL:
{today_content}
{pending_str}
{history_str}"""

        result = self._call(system, user, json_mode=True)

        try:
            parsed = json.loads(result)
            return parsed.get("suggestions", [])
        except json.JSONDecodeError:
            return []

    def generate_weekly_review(self, entries: list) -> dict:
        """Generate comprehensive weekly review"""
        entries_text = ""
        for entry in entries:
            entries_text += f"""
--- {entry.get('date', 'Unknown')} ---
Summary: {entry.get('summary', 'N/A')}
Mood: {entry.get('mood', 'N/A')}
Energy: {entry.get('energy', 'N/A')}
Themes: {entry.get('themes', 'N/A')}
"""

        system = """You are creating a thoughtful weekly review for someone's personal journal.

Create a comprehensive review that includes:
1. Week Overview (2-3 sentences capturing the week)
2. Key Accomplishments (bullet points)
3. Patterns Noticed (mood trends, energy patterns, recurring themes)
4. Challenges Faced
5. Insights & Reflections
6. Suggestions for Next Week

Write in second person ("You..."). Be insightful, supportive, and specific.

Return JSON:
{
    "overview": "2-3 sentence overview",
    "accomplishments": ["accomplishment1", "accomplishment2"],
    "patterns": {
        "mood_trend": "description of mood pattern",
        "energy_trend": "description of energy pattern",
        "recurring_themes": ["theme1", "theme2"]
    },
    "challenges": ["challenge1", "challenge2"],
    "insights": ["insight1", "insight2"],
    "next_week_suggestions": [
        {"suggestion": "what to do", "why": "reason"}
    ],
    "highlight_of_week": "single best moment or achievement",
    "word_of_week": "one word that captures the week"
}"""

        result = self._call(system, entries_text, json_mode=True, temperature=0.8)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"overview": "Could not generate weekly review"}
