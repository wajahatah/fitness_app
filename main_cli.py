# main.py
import os
import json
from datetime import datetime, date
import pandas as pd

# ===================================
# Base Directories
# ===================================
BASE_DIR = "fitness_app"
USERS_DIR = os.path.join(BASE_DIR, "users")
os.makedirs(USERS_DIR, exist_ok=True)

# ===================================
# Utility Functions
# ===================================
def create_user_folder(username):
    user_dir = os.path.join(USERS_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def user_paths(username):
    user_dir = os.path.join(USERS_DIR, username)
    profile = os.path.join(user_dir, "profile.json")
    meals = os.path.join(user_dir, "meals.csv")
    weights = os.path.join(user_dir, "weights.csv")
    return profile, meals, weights

def init_user_files(username):
    profile_path, meals_path, weights_path = user_paths(username)
    # initialize empty logs
    if not os.path.exists(meals_path):
        pd.DataFrame(columns=["date","time","meal_type","meal_desc","calories","protein","carbs","fats"]).to_csv(meals_path, index=False)
    if not os.path.exists(weights_path):
        pd.DataFrame(columns=["date","time","weight_kg","note"]).to_csv(weights_path, index=False)
    if not os.path.exists(profile_path):
        default = {
            "name": username,
            "sex": "male",
            "age": 25,
            "height_cm": 170,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintenance",
            "protein_factor": 2.0
        }
        with open(profile_path, "w") as f:
            json.dump(default, f, indent=2)

def load_profile(username):
    profile_path, _, _ = user_paths(username)
    with open(profile_path, "r") as f:
        return json.load(f)

def save_profile(username, profile):
    profile_path, _, _ = user_paths(username)
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)

# ===================================
# Fitness Logic
# ===================================
ACTIVITY_MULT = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725
}

def calc_bmr(profile):
    w = profile["weight_kg"]
    h = profile["height_cm"]
    age = profile["age"]
    sex = profile.get("sex","male").lower()
    return 10*w + 6.25*h - 5*age + (5 if sex=="male" else -161)

def calc_targets(profile):
    bmr = calc_bmr(profile)
    activity = profile.get("activity","moderate")
    tdee = bmr * ACTIVITY_MULT.get(activity, 1.55)
    goal = profile.get("goal","maintenance")

    if goal == "fat_loss":
        target_cal = tdee * 0.8
    elif goal == "body_building":
        target_cal = tdee * 1.1
    else:
        target_cal = tdee

    protein = profile.get("protein_factor", 2.0) * profile["weight_kg"]
    carbs = (target_cal * 0.45) / 4
    fats  = (target_cal * 0.25) / 9

    return {
        "calories": round(target_cal,1),
        "protein": round(protein,1),
        "carbs": round(carbs,1),
        "fats": round(fats,1),
        "bmr": round(bmr,1),
        "tdee": round(tdee,1)
    }

# ===================================
# Tracker Functions
# ===================================
def log_meal(username):
    _, meals_path, _ = user_paths(username)
    meal_type = input("Meal (breakfast/lunch/dinner/snack): ").strip()
    meal_desc = input("Meal description: ").strip()
    calories = float(input("Calories (kcal): ").strip())
    protein = float(input("Protein (g): ").strip() or 0)
    carbs = float(input("Carbs (g): ").strip() or 0)
    fats = float(input("Fats (g): ").strip() or 0)

    now = datetime.now()
    entry = {
        "date": now.date().isoformat(),
        "time": now.time().strftime("%H:%M:%S"),
        "meal_type": meal_type,
        "meal_desc": meal_desc,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fats": fats
    }
    df = pd.DataFrame([entry])
    df.to_csv(meals_path, mode='a', header=not pd.io.common.file_exists(meals_path), index=False)
    print("✅ Meal logged.")

def show_daily_summary(username, profile):
    _, meals_path, _ = user_paths(username)
    if not os.path.exists(meals_path):
        print("No meal data yet.")
        return

    df = pd.read_csv(meals_path)
    today = date.today().isoformat()
    today_df = df[df["date"] == today]

    if today_df.empty:
        print("No meals logged today.")
        totals = {"calories":0,"protein":0,"carbs":0,"fats":0}
    else:
        totals = today_df[["calories","protein","carbs","fats"]].sum().to_dict()

    targets = calc_targets(profile)
    print(f"\n--- {username}'s Summary ({today}) ---")
    print(f"Target: {targets}")
    print(f"Consumed: {totals}")
    for k in ["calories","protein","carbs","fats"]:
        consumed = totals.get(k,0)
        targ = targets[k]
        if consumed > targ:
            print(f"⚠️ Exceeded {k} by {consumed - targ:.1f}")
        else:
            print(f"✅ {k} remaining: {targ - consumed:.1f}")

def log_weight(username, profile):
    _, _, weights_path = user_paths(username)
    w = float(input("Enter current weight (kg): ").strip())
    note = input("Note (optional): ").strip()
    now = datetime.now()
    entry = {"date": now.date().isoformat(), "time": now.time().strftime("%H:%M:%S"), "weight_kg": w, "note": note}
    df = pd.DataFrame([entry])
    df.to_csv(weights_path, mode='a', header=not pd.io.common.file_exists(weights_path), index=False)
    profile["weight_kg"] = w
    save_profile(username, profile)
    print("✅ Weight logged and profile updated.")

def show_weight_history(username):
    _, _, weights_path = user_paths(username)
    if not os.path.exists(weights_path):
        print("No weights yet.")
        return
    df = pd.read_csv(weights_path)
    print(df.tail(10).to_string(index=False))

# ===================================
# Profile Update
# ===================================
def update_profile(username, profile):
    print("Leave blank to keep current value.")
    for key in ["name","sex","age","height_cm","weight_kg","activity","goal","protein_factor"]:
        cur = profile.get(key)
        val = input(f"{key} (current: {cur}): ").strip()
        if val == "":
            continue
        if key in ["age"]:
            profile[key] = int(val)
        elif key in ["height_cm","weight_kg","protein_factor"]:
            profile[key] = float(val)
        else:
            profile[key] = val
    save_profile(username, profile)
    print("✅ Profile updated.")

# ===================================
# Authentication
# ===================================
def sign_up():
    username = input("Choose a username: ").strip().lower()
    user_dir = os.path.join(USERS_DIR, username)
    if os.path.exists(user_dir):
        print("⚠️ Username already exists. Try signing in.")
        return None
    create_user_folder(username)
    init_user_files(username)
    print(f"✅ Account created for {username}. You can now sign in.")
    return username

def sign_in():
    username = input("Enter your username: ").strip().lower()
    user_dir = os.path.join(USERS_DIR, username)
    if not os.path.exists(user_dir):
        print("❌ No such user found. Please sign up first.")
        return None
    print(f"✅ Signed in as {username}")
    return username

# ===================================
# Main Menu
# ===================================
def user_menu(username):
    profile = load_profile(username)
    while True:
        print(f"\n--- Welcome, {username}! ---")
        print("1) View profile & targets")
        print("2) Update profile")
        print("3) Log meal")
        print("4) Show today's summary")
        print("5) Log weight")
        print("6) Show weight history")
        print("7) Sign out")
        choice = input("Choose: ").strip()

        if choice == "1":
            print(json.dumps(profile, indent=2))
            print("Targets:", calc_targets(profile))
        elif choice == "2":
            update_profile(username, profile)
        elif choice == "3":
            log_meal(username)
        elif choice == "4":
            show_daily_summary(username, profile)
        elif choice == "5":
            log_weight(username, profile)
        elif choice == "6":
            show_weight_history(username)
        elif choice == "7":
            print("👋 Signed out.")
            break
        else:
            print("Invalid choice.")

def main():
    while True:
        print("\n=== Fitness Tracker ===")
        print("1) Sign up")
        print("2) Sign in")
        print("3) Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            user = sign_up()
        elif choice == "2":
            user = sign_in()
            if user:
                user_menu(user)
        elif choice == "3":
            print("Bye!")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
