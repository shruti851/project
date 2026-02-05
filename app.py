from flask import Flask, render_template, request, redirect, url_for
from bson import ObjectId
from flask import session
from pymongo import MongoClient
from ai_engine import match_startup_investors, match_talent
from ai_routes import *



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




@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/logout')
def logout():
    session.clear()   # removes user_id, role, name, etc.
    return redirect(url_for('login'))


# ---------------- MODULE 1: REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = {
            "name": request.form['name'],
            "email": request.form['email'],
            "password": request.form['password'],  # (hash later)
            "role": request.form['role']
        }
        users_col.insert_one(user)
        return redirect(url_for('login'))
    return render_template('register.html')

# ---------------- MODULE 1: LOGIN ----------------
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

# ---------------- MODULE 2: PITCH IDEA ----------------
@app.route('/pitch', methods=['GET', 'POST'])
def pitch():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        startup = {
            "title": request.form['title'],
            "domain": request.form['domain'],
            "description": request.form['description'],
            "funding": int(request.form['funding']),  # convert to number
            "founder_id": session['user_id']           #  REQUIRED
        }

        startups_col.insert_one(startup)
        return redirect(url_for('dashboard'))  # better UX

    return render_template('pitch_idea.html')


# ---------------- MODULE 2: VIEW STARTUPS ----------------
@app.route('/startups')
def view_startups():
    startups = startups_col.find({
    "founder_id": session['user_id']
})

    return render_template('view_startups.html', startups=startups)

@app.route('/update-startup/<startup_id>', methods=['GET', 'POST'])
def update_startup(startup_id):
    startup = startups_col.find_one({
        "_id": ObjectId(startup_id),
        "founder_id": session['user_id']  # ownership check
    })

    if request.method == 'POST':
        startups_col.update_one(
            {"_id": ObjectId(startup_id)},
            {"$set": {
                "funding": request.form['funding'],
                "team": request.form['team'],
                "visibility": request.form['visibility']
            }}
        )
        return redirect('/view-startups')

    return render_template('update_startup.html', startup=startup)


# ---------------- MODULE 3: CREATE OPEN ROLE (FOUNDER) ----------------
@app.route('/create-role', methods=['GET', 'POST'])
def create_role():
    if request.method == 'POST':
        role = {
    "startup_title": request.form['startup_title'],
    "role_name": request.form['role_name'],
    "skills": request.form['skills'],
    "founder_id": session['user_id']   
}

        db.roles.insert_one(role)
        return redirect(url_for('view_roles'))
    return render_template('create_role.html')


# ---------------- VIEW OPEN ROLES (TALENT) ----------------
@app.route('/roles')
def view_roles():
    roles = roles_col.find({
    "founder_id": session['user_id']
})

    return render_template('view_roles.html', roles=roles)


# ---------------- APPLY FOR ROLE (TALENT) ----------------
@app.route('/apply/<role_id>', methods=['GET', 'POST'])
def apply_role(role_id):
    from bson import ObjectId

    role = db.roles.find_one({"_id": ObjectId(role_id)})

    if request.method == 'POST':
        application = {
            "role_id": role_id,
            "talent_name": request.form['talent_name'],
            "email": request.form['email'],
            "skills": request.form['skills'],
            "status": "Pending"
        }
        db.applications.insert_one(application)
        return redirect(url_for('view_roles'))

    return render_template('apply_role.html', role=role)

@app.route('/ai-skill-match')
def ai_skill_match():
    if 'user_id' not in session or session.get('role') != 'Talent':
        return redirect(url_for('login'))

    # Fetch talent profile
    talent = users_col.find_one({"_id": session['user_id']})

    # Dummy AI recommendations (for now)
    recommended_roles = list(roles_col.find().limit(5))

    return render_template(
        'ai_skill_match.html',
        talent=talent,
        roles=recommended_roles
    )



# ---------------- VIEW APPLICATIONS (FOUNDER) ----------------
@app.route('/applications')
def view_applications():
    applications = list(db.applications.find())
    return render_template('view_applications.html', applications=applications)

# ---------------- MODULE 4: INVESTOR VIEW STARTUPS ----------------
@app.route('/investor/startups')
def investor_view_startups():
    startups = list(startups_col.find())
    return render_template('investor_startups.html', startups=startups)


# ---------------- INVESTOR SEND FUNDING REQUEST ----------------
@app.route('/fund/<startup_id>', methods=['GET', 'POST'])
def fund_startup(startup_id):
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})

    if request.method == 'POST':
        request_data = {
    "startup_id": startup_id,
    "founder_id": startup['founder_id'],   #  ADD HERE
    "investor_id": session['user_id'],      # optional but good
    "investor_name": request.form['investor_name'],
    "amount": request.form['amount'],
    "equity": request.form['equity'],
    "status": "Pending"
}

        funding_requests_col.insert_one(request_data)
        return redirect(url_for('investor_view_startups'))

    return render_template('fund_startup.html', startup=startup)


# ---------------- FOUNDER VIEW FUNDING REQUESTS ----------------
@app.route('/funding-requests')
def view_funding_requests():
    requests = funding_requests_col.find({
        "founder_id": session['user_id']
    })
    return render_template('view_funding_requests.html', requests=requests)



# ---------------- ACCEPT / REJECT OFFER ----------------
@app.route('/funding-decision/<request_id>/<decision>')
def funding_decision(request_id, decision):
    funding_requests_col.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": decision}}
    )

    funding_decisions_col.insert_one({
        "request_id": request_id,
        "decision": decision
    })

    return redirect(url_for('view_funding_requests'))

@app.route('/invest/<startup_id>', methods=['POST'])
def invest(startup_id):
    investment = {
        "startup_id": startup_id,
        "investor_id": session['user_id'],
        "amount": request.form['amount'],
        "status": "Pending"
    }
    investments_col.insert_one(investment)
    return redirect('/investor/portfolio')

@app.route('/investor/portfolio')
def investor_portfolio():
    investments = investments_col.find({
        "investor_id": session['user_id']
    })
    return render_template(
        "investor_portfolio.html",
        investments=investments
    )
@app.route('/investor/insights')
def market_insights():
    pipeline = [
        {"$group": {"_id": "$domain", "count": {"$sum": 1}}}
    ]
    domain_stats = startups_col.aggregate(pipeline)
    return render_template(
        "market_insights.html",
        stats=domain_stats
)
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect('/login')

    role = session['role']
    user_id = session['user_id']

    analytics_data = {}

    # ---------- FOUNDER ANALYTICS ----------
    if role == "Founder":
        analytics_data = {
            "team_growth": [2, 4, 6, 8],
            "investor_interest": [1, 3, 5, 7],
            "pitch_performance": [60, 70, 85, 90]
        }

    # ---------- INVESTOR ANALYTICS ----------
    elif role == "Investor":
        analytics_data = {
            "portfolio_value": [10, 15, 20, 30],
            "risk_analysis": [30, 25, 20, 15],
            "sector_trends": [40, 30, 20, 10]
        }

    # ---------- TALENT ANALYTICS ----------
    elif role == "Talent":
        analytics_data = {
            "skill_demand": [80, 70, 60, 90],
            "active_opportunities": [3, 6, 9, 12],
            "profile_visibility": [50, 65, 75, 90]
        }

    return render_template(
        "analytics.html",
        role=role,
        analytics=analytics_data
    )

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
   


    role = session['role']
    name = session['name']

    stats = {}

    if role == "Founder":
        stats = {
            "startups": startups_col.count_documents({"founder_id": session['user_id']}),
            "funding": funding_requests_col.count_documents({"founder_id": session['user_id']}),
            "roi": "_"
        }

    elif role == "Talent":
        stats = {
            "applications": applications_col.count_documents({"talent_id": session['user_id']}),
            "roi": "_"
        }

    elif role == "Investor":
        stats = {
            "funding": funding_requests_col.count_documents({"investor_id": session['user_id']}),
            "roi": "18%"
        }

    chart_data = [
        stats.get("startups", 0),
        stats.get("funding", 0),
        20
    ]

    return render_template(
        "dashboard.html",
        name=name,
        role=role,
        stats=stats,
        chart_data=chart_data
    )
@app.route('/ai/investor-match/<startup_id>')
def investor_match(startup_id):
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    investors = list(users_col.find())

    matches = match_startup_investors(
        startup["description"],
        investors
    )

    return render_template(
        "investor_match.html",
        startup=startup,
        matches=matches
    )
@app.route('/ai/talent-match/<startup_id>')
def talent_match(startup_id):
    startup = startups_col.find_one({"_id": ObjectId(startup_id)})
    talents = list(users_col.find())

    matches = match_talent(
        startup["skills_required"],
        talents
    )

    return render_template(
        "talent_match.html",
        startup=startup,
        matches=matches
    )
@app.route('/feedback', methods=['POST'])
def feedback():
    feedback_col.insert_one({
        "startup_id": request.form["startup_id"],
        "user_id": request.form["user_id"],
        "rating": int(request.form["rating"])
    })
    return redirect('/dashboard')


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        threaded=False,
        use_reloader=False
    )

