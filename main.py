# app.py
import streamlit as st
import sqlite3
import pandas as pd
import datetime as dt
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Any

# -------------------------
# OOP: Abstraction + Encapsulation
# -------------------------
class Habit(ABC):
    def __init__(self, name: str, target_per_day: float):
        self._name = name
        self._target_per_day = float(target_per_day)
        self.__streak_days = 0  # encapsulated (private)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def target(self) -> float:
        return self._target_per_day

    def _update_streak(self, logs_df: pd.DataFrame):
        """Update streak based on consecutive days meeting target."""
        if logs_df.empty:
            self.__streak_days = 0
            return
        # Create a date -> met_target map
        logs_df = logs_df.copy()
        logs_df["date"] = pd.to_datetime(logs_df["date"]).dt.date
        met = logs_df.groupby("date")["amount"].sum().apply(lambda x: x >= self.target)
        # Count consecutive days up to today where met is True
        today = dt.date.today()
        streak = 0
        d = today
        while d in met.index and met.loc[d]:
            streak += 1
            d = d - dt.timedelta(days=1)
        # If today not met, see if yesterday starts the streak
        if streak == 0:
            d = today - dt.timedelta(days=1)
            while d in met.index and met.loc[d]:
                streak += 1
                d = d - dt.timedelta(days=1)
        self.__streak_days = streak

    def get_streak(self) -> int:
        return self.__streak_days

    @abstractmethod
    def recommendation(self, recent_df: pd.DataFrame) -> str:
        """Polymorphic recommendation based on recent logs."""
        ...

    def refresh_metrics(self, logs_df: pd.DataFrame):
        self._update_streak(logs_df)

class ExerciseHabit(Habit):
    def recommendation(self, recent_df: pd.DataFrame) -> str:
        last7 = recent_df[recent_df["date"] >= (dt.date.today() - dt.timedelta(days=6))]
        avg = last7["amount"].mean() if not last7.empty else 0
        tip = "Great pace—consider adding a rest day" if avg >= self.target else \
              "Try 10–15% incremental increase next week"
        return f"Exercise: avg {avg:.1f} min/day vs target {self.target:.0f}. {tip}."

class StudyHabit(Habit):
    def recommendation(self, recent_df: pd.DataFrame) -> str:
        last7 = recent_df[recent_df["date"] >= (dt.date.today() - dt.timedelta(days=6))]
        consistency = last7.groupby("date")["amount"].sum().ge(self.target).mean() if not last7.empty else 0
        tip = "Lock in a Pomodoro block (25/5) at a fixed hour." if consistency < 0.6 else \
              "Level up: add spaced-repetition review."
        return f"Study: {consistency*100:.0f}% of last 7 days met target. {tip}"

class SleepHabit(Habit):
    def recommendation(self, recent_df: pd.DataFrame) -> str:
        last7 = recent_df[recent_df["date"] >= (dt.date.today() - dt.timedelta(days=6))]
        variance = last7["amount"].std() if not last7.empty else None
        if variance is None:
            msg = "No recent data. Aim for a consistent bedtime window (±30 min)."
        else:
            msg = "Bedtime consistency looks good—maintain routine." if variance <= 0.75 else \
                  "Large variance—set a fixed screen-off time 1 hour before bed."
        return f"Sleep: std dev {0 if variance is None else variance:.2f} hrs. {msg}"

# -------------------------
# Factory (helps polymorphism/extensibility)
# -------------------------
class HabitFactory:
    TYPES = {
        "Exercise (minutes)": ExerciseHabit,
        "Study (minutes)": StudyHabit,
        "Sleep (hours)": SleepHabit,
    }

    @staticmethod
    def create(h_type: str, name: str, target_per_day: float) -> Habit:
        cls = HabitFactory.TYPES[h_type]
        return cls(name, target_per_day)

# -------------------------
# Persistence Layer (Repository)
# -------------------------
class SQLiteRepo:
    def __init__(self, path: str = "habits.db"):
        self.path = path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def _init_db(self):
        with self._conn() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS habits(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    target REAL NOT NULL
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS logs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    FOREIGN KEY(habit_id) REFERENCES habits(id)
                )
            """)

    # Habits
    def add_habit(self, name: str, h_type: str, target: float) -> int:
        with self._conn() as con:
            cur = con.execute("INSERT INTO habits(name,type,target) VALUES(?,?,?)",
                              (name, h_type, float(target)))
            return cur.lastrowid

    def list_habits(self) -> pd.DataFrame:
        with self._conn() as con:
            return pd.read_sql_query("SELECT * FROM habits ORDER BY id DESC", con)

    def delete_habit(self, habit_id: int):
        with self._conn() as con:
            con.execute("DELETE FROM logs WHERE habit_id=?", (habit_id,))
            con.execute("DELETE FROM habits WHERE id=?", (habit_id,))

    # Logs
    def add_log(self, habit_id: int, date: dt.date, amount: float):
        with self._conn() as con:
            con.execute("INSERT INTO logs(habit_id,date,amount) VALUES(?,?,?)",
                        (habit_id, date.isoformat(), float(amount)))

    def get_logs(self, habit_id: int) -> pd.DataFrame:
        with self._conn() as con:
            df = pd.read_sql_query(
                "SELECT date, amount FROM logs WHERE habit_id=? ORDER BY date ASC",
                con, params=(habit_id,)
            )
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        return df

# -------------------------
# In-memory repository (when DB disabled)
# -------------------------
class MemoryRepo:
    def __init__(self):
        self._habits: Dict[int, Dict[str, Any]] = {}
        self._logs: Dict[int, List[Tuple[dt.date, float]]] = {}
        self._next_id = 1

    def add_habit(self, name: str, h_type: str, target: float) -> int:
        hid = self._next_id
        self._next_id += 1
        self._habits[hid] = {"id": hid, "name": name, "type": h_type, "target": float(target)}
        self._logs[hid] = []
        return hid

    def list_habits(self) -> pd.DataFrame:
        if not self._habits:
            return pd.DataFrame(columns=["id", "name", "type", "target"])
        return pd.DataFrame(list(self._habits.values())).sort_values("id", ascending=False)

    def delete_habit(self, habit_id: int):
        self._habits.pop(habit_id, None)
        self._logs.pop(habit_id, None)

    def add_log(self, habit_id: int, date: dt.date, amount: float):
        self._logs.setdefault(habit_id, []).append((date, float(amount)))

    def get_logs(self, habit_id: int) -> pd.DataFrame:
        rows = self._logs.get(habit_id, [])
        if not rows:
            return pd.DataFrame(columns=["date", "amount"])
        df = pd.DataFrame(rows, columns=["date", "amount"])
        return df

# -------------------------
# Streamlit App
# -------------------------
st.set_page_config(page_title="Smart Habit Tracker (OOP)", page_icon="✅", layout="wide")
st.title("🧠 Smart Habit Tracker & Recommender (OOP + Streamlit)")

# Sidebar: choose persistence
if "use_db" not in st.session_state:
    st.session_state.use_db = True
use_db = st.sidebar.toggle("Use SQLite persistence", value=st.session_state.use_db, help="Turn off to use in-memory only")
st.session_state.use_db = use_db

# Repo selection
if "repo" not in st.session_state:
    st.session_state.repo = SQLiteRepo() if use_db else MemoryRepo()
else:
    # Switch if user toggled mode
    if use_db and isinstance(st.session_state.repo, MemoryRepo):
        st.session_state.repo = SQLiteRepo()
    elif (not use_db) and isinstance(st.session_state.repo, SQLiteRepo):
        st.session_state.repo = MemoryRepo()
repo = st.session_state.repo

# Add Habit
with st.expander("➕ Add a new habit"):
    cols = st.columns(3)
    h_name = cols[0].text_input("Habit name", placeholder="e.g., Morning Run")
    h_type = cols[1].selectbox("Habit type", list(HabitFactory.TYPES.keys()))
    h_target = cols[2].number_input("Daily target", min_value=0.0, value=30.0, step=5.0, help="minutes for Exercise/Study, hours for Sleep")

    if st.button("Add Habit", type="primary", disabled=not h_name.strip()):
        hid = repo.add_habit(h_name.strip(), h_type, h_target)
        st.success(f"Habit added (id={hid})")

# List & Delete
habits_df = repo.list_habits()
st.subheader("📋 Your Habits")
if habits_df.empty:
    st.info("No habits yet. Add one above.")
else:
    st.dataframe(habits_df, use_container_width=True)
    del_id = st.selectbox("Delete a habit", [None] + habits_df["id"].tolist())
    if st.button("Delete Selected", disabled=(del_id is None)):
        repo.delete_habit(int(del_id))
        st.warning("Habit deleted.")

# Log Progress
st.subheader("📝 Daily Check-in")
if habits_df.empty:
    st.info("Add a habit first to log progress.")
else:
    c1, c2, c3, c4 = st.columns(4)
    sel = c1.selectbox("Habit", habits_df["name"].tolist())
    hrow = habits_df[habits_df["name"] == sel].iloc[0]
    date = c2.date_input("Date", value=dt.date.today())
    amt = c3.number_input("Amount", min_value=0.0, value=30.0, step=5.0)
    if c4.button("Log"):
        repo.add_log(int(hrow["id"]), date, amt)
        st.success("Logged!")

# Dashboard & Recommendations
st.subheader("📈 Dashboard & Recommendations")
if habits_df.empty:
    st.info("Add and log some habits to see charts and tips.")
else:
    pick = st.selectbox("Select habit for insights", habits_df["name"].tolist(), key="dash_pick")
    row = habits_df[habits_df["name"] == pick].iloc[0]
    hid, htype, htarget = int(row["id"]), row["type"], float(row["target"])
    logs = repo.get_logs(hid)

    # Build proper Habit object via factory
    habit_obj = HabitFactory.create(htype, row["name"], htarget)
    habit_obj.refresh_metrics(logs)

    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"**Trend for:** {habit_obj.name} • **Target:** {habit_obj.target:.1f} per day")
        if logs.empty:
            st.info("No logs yet.")
        else:
            # Aggregate by date and show a simple line chart
            chart_df = logs.groupby("date", as_index=False)["amount"].sum().sort_values("date")
            chart_df = chart_df.set_index("date")
            st.line_chart(chart_df["amount"])
            st.caption("Tip: Aim to keep the line at or above your target.")

    with right:
        # st.metric("Current Streak (days)", habit_obj.get_streak())
        recent = logs.copy()
        rec = habit_obj.recommendation(recent)
        st.markdown("### 🔍 Personalized Recommendation")
        st.write(rec)

# Footer
st.markdown("---")
st.caption("OOP pillars: abstract base class (`Habit`), subclasses (`Exercise/Study/Sleep`), encapsulated state (`__streak_days`), polymorphic `recommendation()`; scalable via `HabitFactory` + repository pattern.")
