import json
import random
from pathlib import Path
from time import sleep



# === CONFIGURATION ===
QUESTIONS_FILE = Path("data/Questions_Scenario_Based_v2.json")
GAMELOGIC_FILE = Path("data/gamelogic.json")
USER_DIR = Path("data/users")
USER_DIR.mkdir(parents=True, exist_ok=True)

# === LOAD QUESTIONS & GAME LOGIC ===
with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    all_questions = json.load(f)
with open(GAMELOGIC_FILE, "r", encoding="utf-8") as f:
    logic = json.load(f)

DIFFICULTY_LEVELS = logic["question_engine"]["difficulty_levels"]
XP_WIN = logic["battle_logic"]["xp_award_on_win"]

# === USER PROFILE ===
def load_user(username):
    path = USER_DIR / f"{username}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        profile = {
            "username": username,
            "xp": 0,
            "streak": 0,
            "question_progress": {}
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        return profile

def save_user(profile):
    path = USER_DIR / f"{profile['username']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

# === GET QUESTION ===

def get_question(profile, questions, world):
    pool = []
    progress = profile["question_progress"]
    for q in questions:
        # Strict match by chapter name to world
        if world != "ALL" and q.get("chapter", "").strip() != world.strip():
            continue

        qid = q["id"]
        cooldown = progress.get(qid, {}).get("cooldown", 0)
        if cooldown > 0:
            progress[qid]["cooldown"] -= 1
            continue
        mistakes = progress.get(qid, {}).get("mistakes", 0)
        weight = 1 + (mistakes * 2)
        pool.extend([q] * weight)
    return random.choice(pool) if pool else None
def update_progress(profile, qid, correct):
    from pathlib import Path
    USER_DIR = Path("data/users")
    USER_DIR.mkdir(parents=True, exist_ok=True)
    def save_user(profile):
        path = USER_DIR / f"{profile['username']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
    progress = profile["question_progress"]
    entry = progress.get(qid, {"mistakes": 0, "difficulty_level": 1})
    if correct:
        entry["cooldown"] = 3
    else:
        entry["mistakes"] += 1
        entry["difficulty_level"] = min(entry["difficulty_level"] + 1, 3)
        entry["cooldown"] = 1
    progress[qid] = entry
    save_user(profile)

# === MAIN LOOP ===

# === WORLD SELECTION ===
def choose_world(questions):
    chapters = sorted({q.get("chapter", "mixed bag") for q in questions})
    print("\n🌍 Choose a world to battle in:")
    for i, chap in enumerate(chapters, 1):
        print(f"{i}. {chap}")
    print(f"{len(chapters)+1}. ALL (Use questions from all chapters)")

    choice = input("Enter your choice (1 - {0}): ".format(len(chapters)+1)).strip()
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(chapters):
            return chapters[index-1]
    return "ALL"

# === FILTER QUESTIONS BY CHAPTER ===
def filter_questions_by_chapter(questions, chapter_choice):
    if chapter_choice == "ALL":
        return questions
    return [q for q in questions if q.get("chapter") == chapter_choice]


def battle_loop(profile):
    world = choose_world(all_questions)
    questions = filter_questions_by_chapter(all_questions, world)
    state = {
        "player_hp": logic["player"]["health"],
        "wizard_hp": logic["enemy"]["health"]
    }

    print(f"\n⚔️ Welcome {profile['username'].title()}! XP: {profile['xp']} | Streak: {profile['streak']}")
    print(f"\n🌍 World: {world}\n⚔️ A wizard battle begins! Answer correctly to defeat the wizard.\n")
   

    # Debug: count how many usable questions exist
    available_count = 0
    for q in questions:
        qid = q["id"]
        cooldown = profile["question_progress"].get(qid, {}).get("cooldown", 0)
        if cooldown == 0:
            available_count += 1
    print(f"🧠 Usable questions in world '{world}': {available_count} of {len(questions)}")

    missed_questions = []

    while state["player_hp"] > 0 and state["wizard_hp"] > 0:
        print(f"\n🌍 World: {world}")
        q = get_question(profile, questions, world)
        if not q:
            print(f"📭 You have answered all questions available in this world: {world}.")
            switch = input("🔄 Would you like to switch to a new world? (Y/N): ").strip().upper()
            if switch == "Y":
                world = choose_world(all_questions)
                questions = filter_questions_by_chapter(all_questions, world)
                print(f"\n🌍 Switched to World: {world}")

                # Count usable questions after switching
                available_count = 0
                for q in questions:
                    qid = q["id"]
                    cooldown = profile["question_progress"].get(qid, {}).get("cooldown", 0)
                    if cooldown == 0:
                        available_count += 1
                print(f"🧠 Usable questions in world '{world}': {available_count} of {len(questions)}")
                continue
            else:
                print("⏳ Repeating World...")
                continue


        print(f"🧠 Question: {q.get('question') or q.get('text')}\n")
        for choice in q.get("choices", []):
            print(choice)
        print()
        player_input = input("🔤 Choose your answer (A-D): ").upper().strip()
        print("\n")
        correct_letter = (q.get("correct_answer", "") or "X").strip()[0].upper()
        is_correct = player_input == correct_letter
        qid = q["id"]
        update_progress(profile, qid, is_correct)

        difficulty = profile["question_progress"][qid]["difficulty_level"]
        dmg_conf = DIFFICULTY_LEVELS[str(difficulty)]
        player_dmg = dmg_conf["player_damage_on_wrong"]
        enemy_dmg = dmg_conf["enemy_damage_on_correct"]

        if is_correct:
            state["wizard_hp"] -= enemy_dmg
            profile["xp"] += XP_WIN
            print("💥 Correct!")
            print(f"You hit the wizard for {enemy_dmg} damage.")
        else:
            state["player_hp"] -= player_dmg
            profile["streak"] = 0
            missed_questions.append(q)
            print(f"🧙‍♂️ Wrong! The wizard strikes you for {player_dmg} damage.")
            print(f"\n📢 Correct Answer was: {q.get('correct_answer')}")

        print(f"🧍 HP: {state['player_hp']} | 🧙 HP: {state['wizard_hp']} | ⭐ XP: {profile['xp']} | 🔥 Streak: {profile['streak']}")
        print("-" * 80)
        print()
        sleep(0.5)

    if state["player_hp"] <= 0:
        print("☠️ Defeated. Try again.")
    elif state["wizard_hp"] <= 0:
        print("🏆 Victory! You defeated the wizard.")
        profile["streak"] += 1

    if missed_questions:
        print(f"\n📚 Review Mode Available: You missed {len(missed_questions)} question(s).")
        review_choice = input("Would you like to review them now? (Y/N): ").strip().upper()
        if review_choice == 'Y':
            for q in missed_questions:
                print(f"🧠 Review: {q.get('question') or q.get('text')}\n")
                for choice in q.get("choices", []):
                    print(choice)
                print(f"📢 Correct Answer: {q.get('correct_answer')}")
                print("-" * 80)
                print()

# === MAIN ENTRYPOINT ===
if __name__ == "__main__":
    username = input("👤 Enter your username: ").strip().lower()
    path = USER_DIR / f"{username}.json"
    is_new_user = not path.exists()
    profile = load_user(username)
    # ⏮️ Reset cooldowns at login
    for qid in profile["question_progress"]:
        profile["question_progress"][qid]["cooldown"] = 0
    if is_new_user:
        print(f"👋 Welcome, {username.title()}! Your adventure begins now.")
    else:
        print(f"👋 Welcome back, {username.title()}!")

    while True:
        battle_loop(profile)
        save_user(profile)
        again = input("⚔️ Battle again? (Y/N): ").strip().upper()
        if again != 'Y':
            break

    print(f"👋 Goodbye, {profile['username'].title()}! Final XP: {profile['xp']} | Streak: {profile['streak']}")
