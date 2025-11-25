"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# --- Database setup (SQLite + SQLAlchemy) ---
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    schedule = Column(String(200), nullable=True)
    max_participants = Column(Integer, nullable=True)
    participants = relationship("Participant", back_populates="activity", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True)
    email = Column(String(200), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    activity = relationship("Activity", back_populates="participants")


def init_db():
    """Create DB/tables and populate initial data if empty."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        count = session.query(Activity).count()
        if count == 0:
            # initial data previously in-memory
            seed = {
                "Chess Club": {
                    "description": "Learn strategies and compete in chess tournaments",
                    "schedule": "Fridays, 3:30 PM - 5:00 PM",
                    "max_participants": 12,
                    "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
                },
                "Programming Class": {
                    "description": "Learn programming fundamentals and build software projects",
                    "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
                    "max_participants": 20,
                    "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
                },
                "Gym Class": {
                    "description": "Physical education and sports activities",
                    "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
                    "max_participants": 30,
                    "participants": ["john@mergington.edu", "olivia@mergington.edu"]
                },
                "Soccer Team": {
                    "description": "Join the school soccer team and compete in matches",
                    "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
                    "max_participants": 22,
                    "participants": ["liam@mergington.edu", "noah@mergington.edu"]
                },
                "Basketball Team": {
                    "description": "Practice and play basketball with the school team",
                    "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
                    "max_participants": 15,
                    "participants": ["ava@mergington.edu", "mia@mergington.edu"]
                },
                "Art Club": {
                    "description": "Explore your creativity through painting and drawing",
                    "schedule": "Thursdays, 3:30 PM - 5:00 PM",
                    "max_participants": 15,
                    "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
                },
                "Drama Club": {
                    "description": "Act, direct, and produce plays and performances",
                    "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
                    "max_participants": 20,
                    "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
                },
                "Math Club": {
                    "description": "Solve challenging problems and participate in math competitions",
                    "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
                    "max_participants": 10,
                    "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
                },
                "Debate Team": {
                    "description": "Develop public speaking and argumentation skills",
                    "schedule": "Fridays, 4:00 PM - 5:30 PM",
                    "max_participants": 12,
                    "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
                }
            }

            for name, data in seed.items():
                act = Activity(name=name, description=data.get("description"), schedule=data.get("schedule"), max_participants=data.get("max_participants"))
                session.add(act)
                session.flush()  # populate act.id
                for email in data.get("participants", []):
                    p = Participant(email=email, activity_id=act.id)
                    session.add(p)
            session.commit()
    finally:
        session.close()


@app.on_event("startup")
def on_startup():
    # ensure database exists and populate initial data
    init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    session = SessionLocal()
    try:
        activities = {}
        for act in session.query(Activity).all():
            activities[act.name] = {
                "description": act.description,
                "schedule": act.schedule,
                "max_participants": act.max_participants,
                "participants": [p.email for p in act.participants]
            }
        return activities
    finally:
        session.close()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity (persisted in DB)"""
    session = SessionLocal()
    try:
        act = session.query(Activity).filter(Activity.name == activity_name).first()
        if not act:
            raise HTTPException(status_code=404, detail="Activity not found")

        # check if already signed up
        existing = session.query(Participant).filter(Participant.activity_id == act.id, Participant.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        # check capacity
        if act.max_participants is not None and len(act.participants) >= act.max_participants:
            raise HTTPException(status_code=400, detail="Activity is full")

        p = Participant(email=email, activity_id=act.id)
        session.add(p)
        session.commit()
        return {"message": f"Signed up {email} for {activity_name}"}
    finally:
        session.close()


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity (DB)"""
    session = SessionLocal()
    try:
        act = session.query(Activity).filter(Activity.name == activity_name).first()
        if not act:
            raise HTTPException(status_code=404, detail="Activity not found")

        participant = session.query(Participant).filter(Participant.activity_id == act.id, Participant.email == email).first()
        if not participant:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        session.delete(participant)
        session.commit()
        return {"message": f"Unregistered {email} from {activity_name}"}
    finally:
        session.close()
