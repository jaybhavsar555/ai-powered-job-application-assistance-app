from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from app.application.agents.base import OSAgent
from app.core.config import get_settings

class QAUpdate(BaseModel):
    question: str = Field(description="The profile or screening question (e.g., 'Address', 'Phone Number', 'Do you have Python experience?')")
    answer: str = Field(description="The extracted answer based on the user's message.")
    tags: List[str] = Field(description="Tags like 'contact', 'location', 'skills', etc.")

class ProfileUpdaterOutput(BaseModel):
    updated_resume_text: str = Field(description="The completely rewritten resume text in Markdown, incorporating the user's updates. Must preserve all previous formatting and sections, only altering what the user requested.")
    qa_updates: List[QAUpdate] = Field(description="Any specific QA profile fields that were updated (e.g., location, phone).")
    agent_reply: str = Field(description="A friendly, concise reply confirming what was changed (e.g., 'I updated your phone number on your resume and in your profile!').")

class ProfileUpdaterAgent(OSAgent):
    name = "ProfileUpdaterAgent"
    description = "Updates the master resume and QA profile based on natural language chat."

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        chat_message = state.get("chat_message", "")
        resume_text = state.get("resume_text", "")
        
        settings = get_settings()
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2
        ).with_structured_output(ProfileUpdaterOutput)
        
        prompt = PromptTemplate(
            template="""You are a Profile and Resume Assistant. 
The user is asking you to update their professional profile and master resume.

User's Request: {chat_message}

Current Master Resume:
{resume_text}

Instructions:
1. Parse the user's request to understand what they want to change (e.g., add a skill, change location, update phone number).
2. Rewrite the `Current Master Resume` incorporating these changes. You must output the ENTIRE resume, preserving all original markdown formatting, bullet points, and sections, unless the user explicitly requested to remove them. Do not truncate the resume.
3. If the user updated basic profile data (like address, phone, location, links, or specific screening questions), extract those into `qa_updates` so they can be saved to the autofill database.
4. Write a friendly, concise `agent_reply` confirming what you did.

Output your response adhering to the requested schema.
""",
            input_variables=["chat_message", "resume_text"]
        )
        
        chain = prompt | llm
        try:
            result: ProfileUpdaterOutput = await chain.ainvoke({
                "chat_message": chat_message,
                "resume_text": resume_text
            })
            
            return {
                "updated_resume_text": result.updated_resume_text,
                "qa_updates": [qa.model_dump() for qa in result.qa_updates],
                "agent_reply": result.agent_reply,
            }
        except Exception as e:
            return {
                "updated_resume_text": resume_text,
                "qa_updates": [],
                "agent_reply": f"Sorry, I ran into an error trying to process your update: {e}"
            }
