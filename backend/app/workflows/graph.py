from langgraph.graph import StateGraph, END
from app.workflows.state import AgentState
from app.application.agents.registry import agent_registry
import asyncio
import json

async def job_intake_node(state: AgentState):
    agent = agent_registry.get_agent("job_intake_agent")
    
    # Pack required inputs into state format expected by agent
    agent_state = {
        "job_description_raw": "Mock raw job content from URL",
        "title": "Software Engineer",
        "company": "Tech Corp"
    }
    
    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    return {
        "messages": ["Extracted requirements and normalized job description."], 
        "job_details": result.get("normalized_job")
    }

async def company_research_node(state: AgentState):
    # Place holder for Company Research Agent
    await asyncio.sleep(2)
    return {
        "messages": ["Researched target company successfully."], 
        "company_research": {"stack": ["Python", "Kubernetes"], "funding": "Series B"}
    }

async def ats_analysis_node(state: AgentState):
    agent = agent_registry.get_agent("ats_analyzer")
    job_str = json.dumps(state.get("job_details", {}))
    base_resume = "Mock base resume with Python and SQL."
    
    agent_state = {
        "resume_json": base_resume,
        "job_description": job_str
    }
    
    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    ats_res = result.get("ats_score", {})
    
    return {
        "messages": [
            f"ATS Analysis completed. Score: {ats_res.get('score')}%.",
            f"Missing critical skills: {', '.join(ats_res.get('missing_skills', []))}"
        ], 
        "ats_score": ats_res.get("score"),
        "company_research": {"missing_skills": ats_res.get("missing_skills", [])} # Stashing missing skills in state
    }

async def resume_optimization_node(state: AgentState):
    agent = agent_registry.get_agent("resume_optimizer")
    job_str = json.dumps(state.get("job_details", {}))
    base_resume = "Mock base resume with Python and SQL."
    
    # We stashed missing skills in company_research for now
    ats_score = {"missing_skills": state.get("company_research", {}).get("missing_skills", [])}
    
    agent_state = {
        "resume_json": base_resume,
        "ats_score": ats_score,
        "job_description": job_str
    }
    
    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    opt_res = result.get("optimized_resume", {})
    
    return {
        "messages": [
            "Optimized resume tailored to JD.",
            f"Successfully added keywords: {', '.join(opt_res.get('added_keywords', []))}"
        ], 
        "tailored_resume": opt_res
    }

async def cover_letter_node(state: AgentState):
    agent = agent_registry.get_agent("cover_letter_agent")
    job_str = json.dumps(state.get("job_details", {}))
    resume_str = json.dumps(state.get("tailored_resume", {}))
    company_str = json.dumps(state.get("company_research", {}))
    
    agent_state = {
        "optimized_resume": resume_str,
        "job_description": job_str,
        "company_research": company_str
    }
    
    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    cl_res = result.get("cover_letter", {})
    
    return {
        "messages": [
            "Generated highly personalized Cover Letter.",
            f"Hooks used: {', '.join(cl_res.get('hooks_used', []))}"
        ], 
        "cover_letter": cl_res.get("content"),
        "requires_human_approval": True
    }

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("Job Intake Agent", job_intake_node)
    workflow.add_node("Company Research Agent", company_research_node)
    workflow.add_node("ATS Analyzer", ats_analysis_node)
    workflow.add_node("Resume Optimizer", resume_optimization_node)
    workflow.add_node("Cover Letter Agent", cover_letter_node)
    
    workflow.set_entry_point("Job Intake Agent")
    
    workflow.add_edge("Job Intake Agent", "Company Research Agent")
    workflow.add_edge("Company Research Agent", "ATS Analyzer")
    workflow.add_edge("ATS Analyzer", "Resume Optimizer")
    workflow.add_edge("Resume Optimizer", "Cover Letter Agent")
    workflow.add_edge("Cover Letter Agent", END)
    
    return workflow.compile()

app_graph = build_graph()
