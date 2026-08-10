from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class DBBase:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DBUser(Base, DBBase):
    __tablename__ = "users"
    email = Column(String, unique=True, index=True, nullable=False)
    auth_provider = Column(String, default="local")
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # admin | user | demo
    
    wiki_entities = relationship("DBWikiEntity", back_populates="user")
    resumes = relationship("DBResume", back_populates="user")
    jobs = relationship("DBJob", back_populates="user")

class DBWikiEntity(Base, DBBase):
    __tablename__ = "wiki_entities"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String, nullable=False, index=True) # company, skill, story, project
    title = Column(String, nullable=False)
    content = Column(JSONB, default=dict)
    vector_id = Column(UUID(as_uuid=True), nullable=True) # for Qdrant linking
    
    user = relationship("DBUser", back_populates="wiki_entities")

class DBAgentEventLog(Base, DBBase):
    __tablename__ = "agent_event_logs"
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    agent_name = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    evidence = Column(JSONB, default=dict)
    
    application = relationship("DBApplication", back_populates="event_logs")

class DBCompany(Base, DBBase):
    __tablename__ = "companies"
    name = Column(String, nullable=False, index=True)
    research_data = Column(JSONB, default=dict)
    
    jobs = relationship("DBJob", back_populates="company")
    recruiters = relationship("DBRecruiter", back_populates="company")

class DBJob(Base, DBBase):
    __tablename__ = "jobs"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    url = Column(String, nullable=True)
    role_title = Column(String, nullable=False)
    description_raw = Column(String, nullable=False)
    description_normalized = Column(JSONB, default=dict)
    status = Column(String, default="Imported")
    
    user = relationship("DBUser", back_populates="jobs")
    company = relationship("DBCompany", back_populates="jobs")
    application = relationship("DBApplication", back_populates="job", uselist=False)

class DBResume(Base, DBBase):
    __tablename__ = "resumes"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    content = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    
    user = relationship("DBUser", back_populates="resumes")

class DBApplication(Base, DBBase):
    __tablename__ = "applications"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    stage = Column(String, default="Wishlist")  # Wishlist…Needs input/Failed/Reapply…Applied…
    workflow_state = Column(JSONB, default=dict)
    
    job = relationship("DBJob", back_populates="application")
    resume_versions = relationship("DBResumeVersion", back_populates="application")
    cover_letters = relationship("DBCoverLetter", back_populates="application")
    messages = relationship("DBMessage", back_populates="application")
    event_logs = relationship("DBAgentEventLog", back_populates="application")

class DBResumeVersion(Base, DBBase):
    __tablename__ = "resume_versions"
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    base_resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    tailored_content = Column(JSONB, default=dict)
    ats_score = Column(Integer, nullable=True)
    feedback = Column(JSONB, default=list)
    
    application = relationship("DBApplication", back_populates="resume_versions")

class DBCoverLetter(Base, DBBase):
    __tablename__ = "cover_letters"
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    content_md = Column(String, nullable=False)
    letter_type = Column(String, default="Standard")
    
    application = relationship("DBApplication", back_populates="cover_letters")

class DBRecruiter(Base, DBBase):
    __tablename__ = "recruiters"
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    linkedin_url = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    company = relationship("DBCompany", back_populates="recruiters")

class DBMessage(Base, DBBase):
    __tablename__ = "messages"
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"))
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True)
    content = Column(String, nullable=False)
    message_type = Column(String, default="Email")
    status = Column(String, default="Draft")
    
    application = relationship("DBApplication", back_populates="messages")
    recruiter = relationship("DBRecruiter")
