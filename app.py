from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson import ObjectId
from ai_engine import match_startup_investors, match_talent

app = Flask(__name__)
app.secret_key = "startup_secret"

# ---------------- MONGODB CONNECTION ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["startup_ecosystem"]

users_col = db["users"]
startups_col = db["startups"]
roles_col = db["roles"]
applications_col = db["applications"]
funding_requests_col = db["funding_requests"]
funding_decisions_col = db["funding_decisions"]
investments_col = db["investments"]
feedback_col = db["ai_feedback"]
matches_col = db["ai_matches"]

# =====================================================
# HOME
# =====================================================

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =====================================================
# REGISTER
# =====================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users_col.insert_one({
            "name": request.form['name'],
            "email": request.form['email'],
            "password": request.form['password'],
            "role": request.form['role']
        })
        return redirect(url_for('login'))

    return render_template('register.html')


# =====================================================
# LOGIN
# =====================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({
            "email": request.form['email'],
            "password": request.form['password']
        })

        if user:
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))

        return "Invalid Credentials"

    return render_template('login.html')


# =====================================================
# DASHBOARD (DYNAMIC + FIXED)
# =====================================================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session['role']
    user_id = session['user_id']

    stats = {}
    labels = []

    if role == "Founder":
        stats = {
            "Startups": startups_col.count_documents({"founder_id": user_id}),
            "Funding Requests": funding_requests_col.count_documents({"founder_id": user_id}),
            "Total Users": users_col.count_documents({})
        }

    elif role == "Investor":
        stats = {
            "Total Startups": startups_col.count_documents({}),
            "My Investments": investments_col.count_documents({"investor_id": user_id}),
            "Total Users": users_col.count_documents({})
        }

    elif role == "Talent":
        stats = {
            "Available Roles": roles_col.count_documents({}),
            "My Applications": applications_col.count_documents({"talent_id": user_id}),
            "Total Startups": startups_col.count_documents({})
        }

    labels = list(stats.keys())
    chart_data = list(stats.values())

    return render_template(
        "dashboard.html",
        name=session['name'],
        role=role,
        stats=stats,
        chart_data=chart_data,
        chart_labels=labels
    )


# =====================================================
# PITCH STARTUP
# =====================================================

@app.route('/pitch', methods=['GET', 'POST'])
def pitch():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        startups_col.insert_one({
            "title": request.form['title'],
            "domain": request.form['domain'],
            "description": request.form['description'],
            "funding": int(request.form['funding']),
            "founder_id": session['user_id']
        })

        return redirect(url_for('dashboard'))

    return render_template('pitch_idea.html')


# =====================================================
# VIEW STARTUPS (FOUNDER)
# =====================================================

@app.route('/view_startups')
def view_startups():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    startups = startups_col.find({
        "founder_id": session['user_id']
    })

    return render_template('view_startups.html', startups=startups)


# =====================================================
# CREATE ROLE
# =====================================================

@app.route('/create-role', methods=['GET', 'POST'])
def create_role():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        roles_col.insert_one({
            "startup_title": request.form['startup_title'],
            "role_name": request.form['role_name'],
            "skills": request.form['skills'],
            "founder_id": session['user_id']
        })

        return redirect(url_for('view_roles'))

    return render_template('create_role.html')


# =====================================================
# VIEW ROLES
# =====================================================

@app.route('/view_roles')
def view_roles():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    roles = roles_col.find()

    return render_template('view_roles.html', roles=roles)



# =====================================================
# APPLY ROLE (FIXED TALENT ID)
# =====================================================

@app.route('/apply/<role_id>', methods=['GET', 'POST'])
def apply_role(role_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session['role'] != "Talent":
        return "Access Denied"

    role = roles_col.find_one({"_id": ObjectId(role_id)})

    if not role:
        return "Role Not Found"

    if request.method == 'POST':
        applications_col.insert_one({
            "role_id": role_id,
            "talent_id": session['user_id'],
            "talent_name": session['name'],
            "email": request.form['email'],
            "skills": request.form['skills'],
            "status": "Pending"
        })

        return redirect(url_for('my_applications'))

    return render_template('apply_role.html', role=role)

@app.route('/my-applications')
def my_applications():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session['role'] != "Talent":
        return "Access Denied"

    applications = list(applications_col.find({
        "talent_id": session['user_id']
    }))

    for app in applications:
        role = roles_col.find_one({"_id": ObjectId(app["role_id"])})
        app["role_name"] = role["role_name"] if role else "Unknown"

    return render_template(
        "my_applications.html",
        applications=applications
    )

@app.route('/ai/talent-match/<startup_id>')
def ai_talent_match(startup_id):
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    talents = list(users_col.find({"role": "Talent"}))

    matches = match_talent(
        startup.get("description", ""),
        talents
    )

    return render_template(
        "talent_match.html",
        startup=startup,
        matches=matches
    )



# =====================================================
# INVESTOR VIEW STARTUPS
# =====================================================

@app.route('/investor/startups')
def investor_view_startups():
    startups = startups_col.find()
    return render_template('investor_startups.html', startups=startups)


# =====================================================
# INVEST
# =====================================================

@app.route('/invest/<startup_id>', methods=['POST'])
def invest(startup_id):
    investments_col.insert_one({
        "startup_id": startup_id,
        "investor_id": session['user_id'],
        "amount": request.form['amount'],
        "status": "Approved"
    })

    return redirect(url_for('investor_portfolio'))


# =====================================================
# INVESTOR PORTFOLIO (FIXED JOIN)
# =====================================================

@app.route('/investor/portfolio')
def investor_portfolio():
    investments = list(investments_col.find({
        "investor_id": session['user_id']
    }))

    for inv in investments:
        startup = startups_col.find_one({"_id": ObjectId(inv["startup_id"])})
        inv["startup_title"] = startup["title"] if startup else "Unknown"

    return render_template(
        "investor_portfolio.html",
        investments=investments
    )


# =====================================================
# ANALYTICS (REAL COUNTS)
# =====================================================

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect('/login')

    data = {
        "startups": startups_col.count_documents({}),
        "users": users_col.count_documents({}),
        "investments": investments_col.count_documents({})
    }

    return render_template(
        "analytics.html",
        analytics=data,
        role=session['role']
    )


# =====================================================
# AI MATCH
# =====================================================

@app.route('/ai/investor-match/<startup_id>')
def investor_match(startup_id):
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    investors = list(users_col.find({"role": "Investor"}))

    matches = match_startup_investors(
        startup["description"],
        investors
    )

    return render_template(
        "investor_match.html",
        startup=startup,
        matches=matches
    )



# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
