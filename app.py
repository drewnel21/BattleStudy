# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from game.user_loader import load_user, save_user
import json
from pathlib import Path
import random
import socket

app = Flask(__name__)
app.secret_key = "secret"
app.config['JSON_AS_ASCII'] = False

QUESTIONS_FILE = Path("data/Questions_Scenario_Based_v2.json")
with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    all_questions = json.load(f)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        session["username"] = username
        return redirect(url_for("choose_world"))
    return render_template("index.html")

@app.route("/choose-world", methods=["GET", "POST"])
def choose_world():
    chapters = sorted({q.get("chapter", "Mixed") for q in all_questions})
    
    if request.method == "POST":
        # Save selected world
        session["world"] = request.form["world"]
        
        # ✅ Reset battle state
        session["player_hp"] = 100
        session["wizard_hp"] = 100
        session["streak"] = 0
        session.pop("last_result", None)

        return redirect(url_for("battle"))
    
    return render_template("choose_world.html", chapters=chapters)


@app.route("/battle", methods=["GET", "POST"])
def battle():
    username = session.get("username")
    world = session.get("world", "ALL")
    profile = load_user(username)

    if "player_hp" not in session:
        session["player_hp"] = 100
    if "wizard_hp" not in session:
        session["wizard_hp"] = 100
    if "streak" not in session:
        session["streak"] = 0

    for qid in profile["question_progress"]:
        cooldown = profile["question_progress"][qid].get("cooldown", 0)
        if cooldown > 0:
            profile["question_progress"][qid]["cooldown"] = cooldown - 1
    save_user(profile)

    if request.method == "POST":
        qid = request.form["qid"]
        user_answer = request.form["answer"]
        world = request.form["world"]
        question = next((q for q in all_questions if q["id"] == qid), {})
        correct_answer = question.get("correct_answer", "")[0].upper()

        progress = profile["question_progress"].get(qid, {})
        difficulty = progress.get("difficulty_level", 1)

        is_correct = user_answer == correct_answer

        damage_config = {
            "player_damage": {1: 10, 2: 15, 3: 25},
            "wizard_damage": {1: 10, 2: 15, 3: 25},
        }
        dmg_to_wizard = damage_config["wizard_damage"][difficulty]
        dmg_to_player = damage_config["player_damage"][difficulty]

        if is_correct:
            session["wizard_hp"] -= dmg_to_wizard
            profile["xp"] += 10
            session["streak"] += 1
            result = f"Correct! You hit the wizard for {dmg_to_wizard} damage."
        else:
            session["player_hp"] -= dmg_to_player
            session["streak"] = 0
            result = f"Wrong! The wizard hit you for {dmg_to_player} damage.<br>Correct answer: {question.get('correct_answer')}"

        profile["question_progress"][qid] = {
            "cooldown": 3 if is_correct else 1,
            "mistakes": 0 if is_correct else 1,
            "difficulty_level": difficulty if is_correct else min(difficulty + 1, 3)
        }
        save_user(profile)
        session["last_result"] = result

        if session["wizard_hp"] <= 0:
            session["last_result"] += "<br>You defeated the wizard! +50 XP"
            profile["xp"] += 50
            session["wizard_hp"] = 0
            session["player_hp"] = 0
            save_user(profile)

        elif session["player_hp"] <= 0:
            session["last_result"] += "<br>You were defeated by the wizard."

    usable_questions = [
        q for q in all_questions
        if (world == "ALL" or q.get("chapter") == world)
        and profile["question_progress"].get(q["id"], {}).get("cooldown", 0) == 0
    ]
    if not usable_questions:
        return render_template(
            "battle.html",
            username=username,
            world=world,
            profile=profile,
            difficulty=0,
            mistakes=0,
            question=None,
            error_message=f"No available questions in {world}.",
    )


    question = random.choice(usable_questions)
    qid = question["id"]
    progress = profile["question_progress"].get(qid, {})
    difficulty = progress.get("difficulty_level", 1)
    mistakes = progress.get("mistakes", 0)

    return render_template("battle.html",
                           username=username,
                           world=world,
                           question=question,
                           profile=profile,
                           difficulty=difficulty,
                           mistakes=mistakes)

@app.route("/restart", methods=["POST"])
def restart_battle():
    session["player_hp"] = 100
    session["wizard_hp"] = 100
    session["streak"] = 0
    session.pop("last_result", None)
    return redirect(url_for("battle"))

if __name__ == "__main__":
    host_ip = socket.gethostbyname(socket.gethostname())
    print(f"Local network access: http://{host_ip}:5000")
    print("Access on this machine: http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
