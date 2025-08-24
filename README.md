📌 Smart Habit Tracker (OOP + Streamlit)
🚀 Overview

The Smart Habit Tracker is an interactive application built with Object-Oriented Programming (OOP) principles and Streamlit for visualization.
It allows users to track habits, visualize progress, and receive tailored habit recommendations.

The project demonstrates all four pillars of OOP:

Encapsulation: Habit details (private attributes & methods).

Abstraction: Abstract Habit class with core methods.

Inheritance: Specialized habit classes (ExerciseHabit, StudyHabit, SleepHabit).

Polymorphism: Different implementations of recommendation() for each habit type.

🛠️ Features

Add and log daily habits.

Track progress with visual graphs.

Receive personalized recommendations based on habit type.

Streamlit-powered interactive dashboard.

Extendable with future features (gamification, leaderboards).

🏗️ Tech Stack

Python 3.10+

Streamlit (for GUI)

Matplotlib / Plotly (for charts)

SQLite (Optional) for persistent habit storage

📂 Project Structure
📦 SmartHabitTracker
├── habit_tracker.py            
└── README.md             

▶️ How to Run

Clone the repository:

git clone https://github.com/your-username/smart-habit-tracker.git
cd smart-habit-tracker


Install dependencies:

pip install -r requirements.txt


Run Streamlit:

streamlit run habit_tracker.py

📊 Example Habits

ExerciseHabit → Tracks duration and suggests improvements.

StudyHabit → Tracks study hours and recommends Pomodoro technique.

SleepHabit → Tracks sleep hours and suggests consistency improvements.

🌱 Future Extensions

Add gamification (badges, levels, streaks).

Add AI-powered predictions (predict skipped habits).

Add community leaderboard for competition.

Mobile app version with voice logging.

🤝 Contribution

Feel free to fork, improve, and submit pull requests. 🚀
